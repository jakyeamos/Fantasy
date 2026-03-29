from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

import duckdb

from fantasy.intelligence.models import ScorecardInputs, TeamScorecard
from fantasy.intelligence.scorecard_engine import ScorecardEngine, normalize_within_league
from fantasy.lineup.constants import (
    FADING_WINDOW_THRESHOLD,
    PEAK_WINDOW_THRESHOLD,
    TITLE_WINDOW_WEIGHTS,
)
from fantasy.lineup.models import LineupResult, LineupSlotScore

if TYPE_CHECKING:
    pass

_SLOT_SKIP = {"BN", "IR", "TAXI", "BENCH"}


def _slot_skip(slot: str) -> bool:
    u = slot.strip().upper()
    return u in _SLOT_SKIP


def _flex_like(slot: str) -> bool:
    u = slot.strip().upper()
    return u in ("FLEX", "SUPER_FLEX", "SUPERFLEX", "S-FLEX")


def _player_display(conn: duckdb.DuckDBPyConnection, player_id: str) -> str:
    try:
        row = conn.execute(
            "SELECT COALESCE(full_name, player_id) FROM players WHERE player_id = ?",
            [player_id],
        ).fetchone()
        return str(row[0]) if row else player_id
    except Exception:
        return player_id


class LineupEngine:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn
        self._scorecard_engine = ScorecardEngine(conn)

    def _value_proxy(self, inputs: ScorecardInputs, player_id: str) -> float:
        return self._scorecard_engine._value_proxy(inputs, player_id)

    def _iter_active_slots(
        self, inputs: ScorecardInputs
    ) -> list[tuple[str, str, int]]:
        out: list[tuple[str, str, int]] = []
        for i, slot in enumerate(inputs.roster_positions):
            if _slot_skip(slot):
                continue
            if i >= len(inputs.starters):
                break
            pid = inputs.starters[i]
            if not pid:
                continue
            out.append((slot, str(pid), i))
        return out

    def _compute_replacement_level(
        self,
        all_inputs: dict[int, ScorecardInputs],
        slot_label: str,
        *,
        flex_pool: bool,
    ) -> float:
        first_in = next(iter(all_inputs.values()))
        med_avg = float(
            sum(first_in.position_medians.values())
            / max(len(first_in.position_medians), 1)
        )

        values: list[float] = []
        if flex_pool:
            for inputs in all_inputs.values():
                for slot, pid, _ in self._iter_active_slots(inputs):
                    if _flex_like(slot):
                        values.append(self._value_proxy(inputs, pid))
        else:
            for inputs in all_inputs.values():
                for slot, pid, _ in self._iter_active_slots(inputs):
                    if _flex_like(slot):
                        continue
                    if slot.strip().upper() == slot_label.strip().upper():
                        values.append(self._value_proxy(inputs, pid))

        if not values:
            return float(first_in.position_medians.get(slot_label, med_avg))
        values.sort()
        mid = len(values) // 2
        median = values[mid] if len(values) % 2 != 0 else (values[mid - 1] + values[mid]) / 2
        return float(median)

    def compute_all(
        self,
        league_id: str,
        all_inputs: dict[int, ScorecardInputs],
        scorecards: dict[int, TeamScorecard] | None = None,
    ) -> dict[int, LineupResult]:
        """Two-pass lineup computation with optional scorecards for stability scores."""
        if not all_inputs:
            return {}

        # Replacement levels: standard positions
        sample = next(iter(all_inputs.values()))
        position_keys: set[str] = set()
        for slot, _, _ in self._iter_active_slots(sample):
            if not _flex_like(slot):
                position_keys.add(slot.strip().upper())

        repl_by_pos: dict[str, float] = {}
        for pk in position_keys:
            repl_by_pos[pk] = self._compute_replacement_level(
                all_inputs, pk, flex_pool=False
            )

        flex_repl = self._compute_replacement_level(
            all_inputs, "", flex_pool=True
        )

        # Per-slot-index raw scores, then normalize per index across rosters
        roster_ids = list(all_inputs.keys())
        max_slots = max(
            (len(self._iter_active_slots(inp)) for inp in all_inputs.values()),
            default=0,
        )
        raw_by_slot: list[dict[int, float]] = [{} for _ in range(max_slots)]

        slot_meta: dict[int, dict[int, tuple[str, str, float, float]]] = {
            rid: {} for rid in roster_ids
        }

        for roster_id, inputs in all_inputs.items():
            for si, (slot, pid, orig_idx) in enumerate(
                self._iter_active_slots(inputs)
            ):
                starter_val = self._value_proxy(inputs, pid)
                if _flex_like(slot):
                    repl = flex_repl
                else:
                    repl = repl_by_pos.get(
                        slot.strip().upper(),
                        float(
                            inputs.position_medians.get(
                                inputs.player_positions.get(pid, "UNKNOWN"),
                                5.0,
                            )
                        ),
                    )
                raw = max(0.0, starter_val - repl)
                raw_by_slot[si][roster_id] = raw
                slot_meta[roster_id][si] = (
                    slot,
                    pid,
                    starter_val,
                    repl,
                )

        norm_by_slot: list[dict[int, float]] = []
        for si in range(max_slots):
            norm_by_slot.append(
                normalize_within_league(raw_by_slot[si])
                if raw_by_slot[si]
                else {}
            )

        ceiling_raw: dict[int, float] = {}
        stability_raw: dict[int, float] = {}
        depth_raw: dict[int, float] = {}

        for roster_id, inputs in all_inputs.items():
            starters_set = set(inputs.starters)
            max_ceiling = self._ceiling_score_raw(
                league_id, roster_id, inputs, starters_set
            )

            if scorecards and roster_id in scorecards:
                frag = float(scorecards[roster_id].fragility)
                stability_raw[roster_id] = max(0.0, min(1.0, 1.0 - frag))
            else:
                stability_raw[roster_id] = 0.5

            bench_vals = [
                self._value_proxy(inputs, pid) for pid in inputs.bench
            ]
            med_avg = float(
                sum(inputs.position_medians.values())
                / max(len(inputs.position_medians), 1)
            )
            depth_count = sum(1 for v in bench_vals if v >= med_avg)
            depth_raw[roster_id] = float(depth_count)

            ceiling_raw[roster_id] = float(max_ceiling)

        ceiling_norm = normalize_within_league(ceiling_raw)
        stability_norm = normalize_within_league(stability_raw)
        depth_norm = normalize_within_league(depth_raw)

        results: dict[int, LineupResult] = {}
        now = datetime.now(timezone.utc).isoformat()

        for roster_id, inputs in all_inputs.items():
            slot_scores: list[LineupSlotScore] = []
            total = 0.0
            for si in range(max_slots):
                if si not in slot_meta[roster_id]:
                    continue
                slot, pid, starter_val, repl = slot_meta[roster_id][si]
                score = float(norm_by_slot[si].get(roster_id, 0.0))
                total += score
                slot_scores.append(
                    LineupSlotScore(
                        position=inputs.player_positions.get(pid, slot),
                        player_id=pid,
                        player_name=_player_display(self._conn, pid),
                        starter_value=float(starter_val),
                        replacement_level=float(repl),
                        score=score,
                    )
                )

            c = TITLE_WINDOW_WEIGHTS["ceiling"] * ceiling_norm.get(
                roster_id, 0.0
            )
            s = TITLE_WINDOW_WEIGHTS["stability"] * stability_norm.get(
                roster_id, 0.0
            )
            d = TITLE_WINDOW_WEIGHTS["depth"] * depth_norm.get(roster_id, 0.0)
            composite = c + s + d

            if composite >= PEAK_WINDOW_THRESHOLD:
                label = "Peak Window"
            elif composite >= FADING_WINDOW_THRESHOLD:
                label = "Fading Window"
            else:
                label = "Outside Window"

            results[roster_id] = LineupResult(
                league_id=league_id,
                roster_id=roster_id,
                computed_at=now,
                slot_scores=slot_scores,
                total_lineup_score=float(total),
                title_window_label=label,
                title_window_composite=float(composite),
                ceiling_score=float(ceiling_norm.get(roster_id, 0.0)),
                stability_score=float(stability_norm.get(roster_id, 0.0)),
                depth_score=float(depth_norm.get(roster_id, 0.0)),
            )

        return results

    def _ceiling_score_raw(
        self,
        league_id: str,
        roster_id: int,
        inputs: ScorecardInputs,
        starters: set[str],
    ) -> float:
        if not starters:
            return 0.0
        placeholders = ",".join(["?"] * len(starters))
        try:
            rows = self._conn.execute(
                f"""
                SELECT MAX(comp_ceiling)
                FROM player_values
                WHERE league_id = ? AND roster_id = ? AND player_id IN ({placeholders})
                """,
                [league_id, roster_id, *list(starters)],
            ).fetchone()
            if rows and rows[0] is not None:
                return float(rows[0])
        except Exception:
            pass
        return max(
            (self._value_proxy(inputs, pid) for pid in inputs.starters if pid),
            default=0.0,
        )
