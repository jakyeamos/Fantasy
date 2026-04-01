from __future__ import annotations

import math
from datetime import datetime, timezone

import duckdb

from fantasy.intelligence.constants import POSITIONAL_CLIFF_AGE
from fantasy.intelligence.models import ScorecardInputs, TeamScorecard
from fantasy.intelligence.scorecard_engine import ScorecardEngine, normalize_within_league
from fantasy.lineup.constants import (
    AGE_CLIFF_PROXIMITY_SEASONS,
    CONTENDER_TIER_FRACTION,
    ELITE_INSULATION_THRESHOLD,
    FADING_WINDOW_THRESHOLD,
    PEAK_WINDOW_THRESHOLD,
    TE_NON_PREMIUM_URGENCY_WEIGHT,
    TITLE_WINDOW_WEIGHTS,
    UPGRADE_LEVERAGE_BASE_EQUITY,
)
from fantasy.lineup.models import LineupResult, LineupSlotScore
from fantasy.recommendation.card_engine import RecommendationCardEngine

_SLOT_SKIP = {"BN", "IR", "TAXI", "BENCH"}
_VALID_CONTEXT_FLAGS = (
    "qb_upgrade",
    "qb_downgrade",
    "coaching_change",
    "depth_chart_competition",
    "injury_recovery",
    "age_cliff_proximity",
    "role_expansion",
    "role_compression",
)


def _slot_skip(slot: str) -> bool:
    return slot.strip().upper() in _SLOT_SKIP


def _flex_like(slot: str) -> bool:
    return slot.strip().upper() in {"FLEX", "SUPER_FLEX", "SUPERFLEX", "S-FLEX"}


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2 != 0:
        return float(ordered[mid])
    return float((ordered[mid - 1] + ordered[mid]) / 2)


def _player_display(conn: duckdb.DuckDBPyConnection, player_id: str) -> str:
    try:
        row = conn.execute(
            "SELECT COALESCE(full_name, player_id) FROM players WHERE player_id = ?",
            [player_id],
        ).fetchone()
        return str(row[0]) if row else player_id
    except duckdb.Error:
        return player_id


def _te_premium_active(inputs: ScorecardInputs) -> bool:
    return bool(inputs.league_settings.get("te_premium", False))


class LineupEngine:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn
        self._scorecard_engine = ScorecardEngine(conn)
        self._card_engine = RecommendationCardEngine(conn)

    def _value_proxy(self, inputs: ScorecardInputs, player_id: str) -> float:
        return self._scorecard_engine._value_proxy(inputs, player_id)

    def _iter_active_slots(self, inputs: ScorecardInputs) -> list[tuple[str, str, int]]:
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
            target = slot_label.strip().upper()
            for inputs in all_inputs.values():
                for slot, pid, _ in self._iter_active_slots(inputs):
                    if _flex_like(slot):
                        continue
                    if slot.strip().upper() == target:
                        values.append(self._value_proxy(inputs, pid))

        if not values:
            return float(first_in.position_medians.get(slot_label, med_avg))
        return _median(values)

    def _contender_pool_ids(self, ceiling_scores: dict[int, float]) -> set[int]:
        if not ceiling_scores:
            return set()
        sorted_ids = sorted(
            ceiling_scores,
            key=lambda roster_id: float(ceiling_scores[roster_id]),
            reverse=True,
        )
        cutoff = max(1, math.ceil(len(sorted_ids) * CONTENDER_TIER_FRACTION))
        return set(sorted_ids[:cutoff])

    def _compute_contender_benchmark(
        self,
        all_inputs: dict[int, ScorecardInputs],
        contender_ids: set[int],
        slot_label: str,
        *,
        flex_pool: bool,
    ) -> tuple[float, bool]:
        fallback = self._compute_replacement_level(
            all_inputs,
            slot_label,
            flex_pool=flex_pool,
        )
        if not contender_ids:
            return fallback, False

        values: list[float] = []
        target = slot_label.strip().upper()
        for roster_id, inputs in all_inputs.items():
            if roster_id not in contender_ids:
                continue
            for slot, pid, _ in self._iter_active_slots(inputs):
                if flex_pool:
                    if _flex_like(slot):
                        values.append(self._value_proxy(inputs, pid))
                    continue
                if _flex_like(slot):
                    continue
                if slot.strip().upper() == target:
                    values.append(self._value_proxy(inputs, pid))

        if len(values) < 2:
            return fallback, False
        return _median(values), True

    def _detect_context_flags(
        self, league_id: str, player_id: str, inputs: ScorecardInputs
    ) -> list[str]:
        flags: list[str] = []
        position = inputs.player_positions.get(player_id, "UNKNOWN").upper()
        age = inputs.player_ages.get(player_id)
        cliff_age = POSITIONAL_CLIFF_AGE.get(position)
        if age is not None and cliff_age is not None:
            if age >= cliff_age - AGE_CLIFF_PROXIMITY_SEASONS:
                flags.append("age_cliff_proximity")

        games_played = inputs.player_games_played.get(player_id)
        if player_id in inputs.starters and games_played is not None and games_played < 8:
            flags.append("injury_recovery")

        try:
            rows = self._conn.execute(
                """
                SELECT flag
                FROM player_context_overrides
                WHERE league_id = ? AND player_id = ?
                """,
                [league_id, player_id],
            ).fetchall()
        except duckdb.Error:
            rows = []

        for row in rows:
            flag = str(row[0] or "")
            if flag in _VALID_CONTEXT_FLAGS and flag not in flags:
                flags.append(flag)

        return [
            flag for flag in _VALID_CONTEXT_FLAGS if flag in flags
        ]

    def compute_all(
        self,
        league_id: str,
        all_inputs: dict[int, ScorecardInputs],
        scorecards: dict[int, TeamScorecard] | None = None,
    ) -> dict[int, LineupResult]:
        if not all_inputs:
            return {}

        roster_ids = list(all_inputs.keys())

        ceiling_raw: dict[int, float] = {}
        stability_raw: dict[int, float] = {}
        depth_raw: dict[int, float] = {}
        for roster_id, inputs in all_inputs.items():
            starters_set = set(inputs.starters)
            ceiling_raw[roster_id] = float(
                self._ceiling_score_raw(league_id, roster_id, inputs, starters_set)
            )
            if scorecards and roster_id in scorecards:
                fragility = float(scorecards[roster_id].fragility)
                stability_raw[roster_id] = max(0.0, min(1.0, 1.0 - fragility))
            else:
                stability_raw[roster_id] = 0.5

            bench_vals = [self._value_proxy(inputs, pid) for pid in inputs.bench]
            med_avg = float(
                sum(inputs.position_medians.values())
                / max(len(inputs.position_medians), 1)
            )
            depth_raw[roster_id] = float(sum(1 for value in bench_vals if value >= med_avg))

        contender_ids = self._contender_pool_ids(ceiling_raw)

        position_keys: set[str] = set()
        for inputs in all_inputs.values():
            for slot, _pid, _ in self._iter_active_slots(inputs):
                if not _flex_like(slot):
                    position_keys.add(slot.strip().upper())

        repl_by_pos: dict[str, float] = {}
        contender_benchmarks: dict[str, float] = {}
        contender_benchmark_used: dict[str, bool] = {}
        for position_key in position_keys:
            repl_by_pos[position_key] = self._compute_replacement_level(
                all_inputs,
                position_key,
                flex_pool=False,
            )
            contender_benchmarks[position_key], contender_benchmark_used[position_key] = (
                self._compute_contender_benchmark(
                    all_inputs,
                    contender_ids,
                    position_key,
                    flex_pool=False,
                )
            )

        flex_replacement = self._compute_replacement_level(all_inputs, "", flex_pool=True)
        flex_contender_benchmark, flex_contender_used = self._compute_contender_benchmark(
            all_inputs,
            contender_ids,
            "",
            flex_pool=True,
        )
        contender_benchmark_used_any = flex_contender_used or any(
            contender_benchmark_used.values()
        )

        max_slots = max(
            (len(self._iter_active_slots(inputs)) for inputs in all_inputs.values()),
            default=0,
        )
        raw_by_slot: list[dict[int, float]] = [{} for _ in range(max_slots)]
        slot_meta: dict[int, dict[int, tuple[str, str, str, float, float]]] = {
            roster_id: {} for roster_id in roster_ids
        }

        for roster_id, inputs in all_inputs.items():
            med_avg = float(
                sum(inputs.position_medians.values())
                / max(len(inputs.position_medians), 1)
            )
            for slot_index, (slot, pid, _orig_idx) in enumerate(self._iter_active_slots(inputs)):
                starter_value = self._value_proxy(inputs, pid)
                player_position = inputs.player_positions.get(pid, slot).upper()
                if _flex_like(slot):
                    replacement_level = flex_replacement
                else:
                    replacement_level = repl_by_pos.get(
                        slot.strip().upper(),
                        float(inputs.position_medians.get(player_position, med_avg)),
                    )
                raw_by_slot[slot_index][roster_id] = max(0.0, starter_value - replacement_level)
                slot_meta[roster_id][slot_index] = (
                    slot,
                    pid,
                    player_position,
                    starter_value,
                    replacement_level,
                )

        norm_by_slot = [
            normalize_within_league(raw) if raw else {}
            for raw in raw_by_slot
        ]
        ceiling_norm = normalize_within_league(ceiling_raw)
        stability_norm = normalize_within_league(stability_raw)
        depth_norm = normalize_within_league(depth_raw)

        results: dict[int, LineupResult] = {}
        now = datetime.now(timezone.utc).isoformat()

        for roster_id, inputs in all_inputs.items():
            slot_scores: list[LineupSlotScore] = []
            total_lineup_score = 0.0
            guard_active = bool(
                scorecards
                and roster_id in scorecards
                and float(scorecards[roster_id].positional_insulation) >= ELITE_INSULATION_THRESHOLD
            )

            for slot_index in range(max_slots):
                if slot_index not in slot_meta[roster_id]:
                    continue
                slot, pid, position, starter_value, replacement_level = slot_meta[roster_id][
                    slot_index
                ]
                contender_benchmark = (
                    flex_contender_benchmark
                    if _flex_like(slot)
                    else contender_benchmarks.get(slot.strip().upper(), replacement_level)
                )
                weak_by_median = starter_value < replacement_level
                weak_relative_to_contender = (
                    starter_value < contender_benchmark and not guard_active
                )
                upgrade_leverage_score = (
                    0.0
                    if guard_active
                    else max(0.0, contender_benchmark - starter_value)
                )
                format_urgency_weight = (
                    TE_NON_PREMIUM_URGENCY_WEIGHT
                    if position == "TE" and not _te_premium_active(inputs)
                    else 1.0
                )
                score = float(norm_by_slot[slot_index].get(roster_id, 0.0))
                total_lineup_score += score
                slot_scores.append(
                    LineupSlotScore(
                        position=position,
                        player_id=pid,
                        player_name=_player_display(self._conn, pid),
                        starter_value=float(starter_value),
                        replacement_level=float(replacement_level),
                        score=score,
                        contender_benchmark=float(contender_benchmark),
                        upgrade_leverage_score=float(upgrade_leverage_score),
                        weak_by_median=weak_by_median,
                        weak_relative_to_contender=weak_relative_to_contender,
                        elite_insulation_guard=guard_active,
                        format_urgency_weight=float(format_urgency_weight),
                        player_context_flags=self._detect_context_flags(league_id, pid, inputs),
                    )
                )

            best_slot = max(
                slot_scores,
                key=lambda slot: (
                    slot.upgrade_leverage_score * slot.format_urgency_weight,
                    slot.upgrade_leverage_score,
                    slot.score,
                ),
                default=None,
            )
            weighted_leverage = (
                best_slot.upgrade_leverage_score * best_slot.format_urgency_weight
                if best_slot
                else 0.0
            )

            ceiling_component = TITLE_WINDOW_WEIGHTS["ceiling"] * ceiling_norm.get(roster_id, 0.0)
            stability_component = TITLE_WINDOW_WEIGHTS["stability"] * stability_norm.get(
                roster_id, 0.0
            )
            depth_component = TITLE_WINDOW_WEIGHTS["depth"] * depth_norm.get(roster_id, 0.0)
            composite = ceiling_component + stability_component + depth_component

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
                total_lineup_score=float(total_lineup_score),
                title_window_label=label,
                title_window_composite=float(composite),
                ceiling_score=float(ceiling_norm.get(roster_id, 0.0)),
                stability_score=float(stability_norm.get(roster_id, 0.0)),
                depth_score=float(depth_norm.get(roster_id, 0.0)),
                contender_benchmark_used=contender_benchmark_used_any,
                upgrade_leverage_point=(
                    f"{best_slot.player_name} ({best_slot.position})"
                    if best_slot
                    else ""
                ),
                upgrade_title_equity_delta=float(
                    min(1.0, weighted_leverage * UPGRADE_LEVERAGE_BASE_EQUITY)
                ),
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
            row = self._conn.execute(
                f"""
                SELECT MAX(comp_ceiling)
                FROM player_values
                WHERE league_id = ? AND roster_id = ? AND player_id IN ({placeholders})
                """,
                [league_id, roster_id, *list(starters)],
            ).fetchone()
            if row and row[0] is not None:
                return float(row[0])
        except duckdb.Error:
            pass
        return max(
            (self._value_proxy(inputs, pid) for pid in inputs.starters if pid),
            default=0.0,
        )

    def attach_recommendation_cards(self, result: LineupResult) -> LineupResult:
        result.recommendation_cards = self._card_engine.build_lineup_cards(result)
        return result
