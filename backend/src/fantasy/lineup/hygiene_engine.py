from __future__ import annotations

import json
from datetime import datetime, timezone

import duckdb

from fantasy.intelligence.models import ScorecardInputs
from fantasy.lineup.constants import (
    CUT_VALUE_FLOOR,
    HYGIENE_MAX_SUGGESTIONS_PER_TYPE,
    STASH_AGE_CEILING,
    STASH_CEILING_FLOOR,
)
from fantasy.lineup.lineup_repo import LineupRepo
from fantasy.lineup.models import HygieneResult, HygieneSuggestion
from fantasy.trade.models import TradeAsset, TradeRequest
from fantasy.trade.package_builder import PackageBuilder
from fantasy.trade.trade_engine import TradeEngine


def _loads(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        return dict(json.loads(raw))
    except json.JSONDecodeError:
        return {}


class HygieneEngine:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn
        self._repo = LineupRepo(conn)
        self._trade_engine = TradeEngine(conn)
        self._package_builder = PackageBuilder(conn)

    def compute(
        self,
        league_id: str,
        roster_id: int,
        inputs: ScorecardInputs,
        direction_label: str,
        all_inputs: dict[int, ScorecardInputs],
    ) -> HygieneResult:
        consolidate = self._consolidation_suggestions(
            league_id, roster_id, inputs, all_inputs, direction_label
        )
        cut = self._cut_suggestions(league_id, roster_id, inputs)
        stash = self._stash_suggestions(league_id, roster_id, inputs)
        taxi = self._taxi_suggestions(league_id, roster_id, inputs)

        ordered = consolidate + cut + stash + taxi
        now = datetime.now(timezone.utc).isoformat()
        return HygieneResult(
            league_id=league_id,
            roster_id=roster_id,
            computed_at=now,
            suggestions=ordered,
        )

    def _cut_suggestions(
        self, league_id: str, roster_id: int, inputs: ScorecardInputs
    ) -> list[HygieneSuggestion]:
        starters_ir_taxi = (
            set(inputs.starters) | set(inputs.ir) | set(inputs.taxi)
        )
        bench = [p for p in inputs.bench if p not in starters_ir_taxi]
        if not bench:
            return []

        rows = self._conn.execute(
            """
            SELECT player_id, lens_direction
            FROM player_values
            WHERE league_id = ? AND roster_id = ? AND player_id IN (
                SELECT UNNEST(?)
            )
            """,
            [league_id, roster_id, bench],
        ).fetchall()
        scored: list[tuple[str, float, str]] = []
        for pid, lens in rows:
            lv = float(lens or 0.0)
            if lv < CUT_VALUE_FLOOR:
                name = self._player_name(pid)
                scored.append((pid, lv, name))
        scored.sort(key=lambda x: x[1])

        out: list[HygieneSuggestion] = []
        for pid, lens, name in scored[:HYGIENE_MAX_SUGGESTIONS_PER_TYPE]:
            reasoning = (
                f"Cutting {name} frees a roster spot for a better waiver target. "
                f"Dynasty value is minimal ({lens:.2f} directional fit)."
            )
            out.append(
                HygieneSuggestion(
                    action_type="cut",
                    primary_player_ids=[pid],
                    primary_player_names=[name],
                    reasoning=reasoning,
                    direction_fit_score=max(0.0, min(1.0, 1.0 - lens)),
                )
            )
        return out

    def _stash_suggestions(
        self, league_id: str, roster_id: int, inputs: ScorecardInputs
    ) -> list[HygieneSuggestion]:
        starters_ir_taxi = (
            set(inputs.starters) | set(inputs.ir) | set(inputs.taxi)
        )
        bench = [p for p in inputs.bench if p not in starters_ir_taxi]
        if not bench:
            return []

        rows = self._conn.execute(
            """
            SELECT player_id, comp_ceiling
            FROM player_values
            WHERE league_id = ? AND roster_id = ? AND player_id IN (
                SELECT UNNEST(?)
            )
            """,
            [league_id, roster_id, bench],
        ).fetchall()
        out: list[HygieneSuggestion] = []
        for pid, ceil in rows:
            age = int(inputs.player_ages.get(pid, 99))
            c = float(ceil or 0.0)
            if age <= STASH_AGE_CEILING and c >= STASH_CEILING_FLOOR:
                name = self._player_name(pid)
                reasoning = (
                    f"Hold {name} — young asset (age {age}) with ceiling upside ({c:.2f})."
                )
                out.append(
                    HygieneSuggestion(
                        action_type="stash",
                        primary_player_ids=[pid],
                        primary_player_names=[name],
                        reasoning=reasoning,
                        direction_fit_score=0.7,
                    )
                )
        return out[:HYGIENE_MAX_SUGGESTIONS_PER_TYPE]

    def _taxi_suggestions(
        self, league_id: str, roster_id: int, inputs: ScorecardInputs
    ) -> list[HygieneSuggestion]:
        cfg = self._repo.get_taxi_config(league_id)
        if cfg is None:
            return []

        occ = self._repo.get_slot_occupancy(league_id, roster_id)
        if occ.get("taxi_total", 0) <= 0:
            return []
        if occ.get("taxi_used", 0) >= occ.get("taxi_total", 0):
            return []

        starters_ir_taxi = (
            set(inputs.starters) | set(inputs.ir) | set(inputs.taxi)
        )
        bench = [p for p in inputs.bench if p not in starters_ir_taxi]
        if not bench:
            return []

        season = int(inputs.season)
        out: list[HygieneSuggestion] = []
        for pid in bench:
            if pid in inputs.taxi:
                continue
            yp = self._years_pro(pid, season, inputs)
            if yp <= cfg.years_pro_cutoff:
                name = self._player_name(pid)
                yword = "years" if yp != 1 else "year"
                reasoning = (
                    f"Move {name} to taxi — eligible ({yp} {yword} pro) and frees a bench spot."
                )
                out.append(
                    HygieneSuggestion(
                        action_type="taxi",
                        primary_player_ids=[pid],
                        primary_player_names=[name],
                        reasoning=reasoning,
                        direction_fit_score=0.6,
                    )
                )
        return out[:HYGIENE_MAX_SUGGESTIONS_PER_TYPE]

    def _years_pro(
        self, player_id: str, season: int, inputs: ScorecardInputs
    ) -> int:
        row = self._conn.execute(
            "SELECT metadata_blob FROM players WHERE player_id = ?",
            [player_id],
        ).fetchone()
        meta = _loads(row[0] if row else None)
        draft_year = meta.get("years_exp") or meta.get("draft_year")
        if draft_year is not None:
            try:
                return max(0, int(season) - int(draft_year))
            except (TypeError, ValueError):
                pass
        age = int(inputs.player_ages.get(player_id, 22))
        return max(0, age - 22)

    def _consolidation_suggestions(
        self,
        league_id: str,
        roster_id: int,
        inputs: ScorecardInputs,
        all_inputs: dict[int, ScorecardInputs],
        direction_label: str,
    ) -> list[HygieneSuggestion]:
        profiles = self._conn.execute(
            """
            SELECT roster_id, owner_display_name
            FROM rosters
            WHERE league_id = ?
            """,
            [league_id],
        ).fetchall()
        name_by_rid = {int(r[0]): str(r[1] or f"Manager {r[0]}") for r in profiles}

        bench_lens = self._conn.execute(
            """
            SELECT player_id, lens_direction
            FROM player_values
            WHERE league_id = ? AND roster_id = ?
            """,
            [league_id, roster_id],
        ).fetchall()
        bench = [p for p in inputs.bench if p not in set(inputs.starters)]
        lens_map = {str(r[0]): float(r[1] or 0.0) for r in bench_lens}
        bench_in_scope = [p for p in bench if p in lens_map]
        if len(bench_in_scope) < 2:
            return []
        bench_in_scope.sort(key=lambda p: lens_map.get(p, 1.0))
        low_pair = bench_in_scope[:2]
        a, b = low_pair[0], low_pair[1]

        target_pid: str | None = None
        target_rid: int | None = None
        for other_rid, oins in all_inputs.items():
            if other_rid == roster_id:
                continue
            for pid in oins.starters + oins.bench:
                lv = self._row_lens(league_id, other_rid, pid)
                if lv >= 0.5:
                    target_pid = pid
                    target_rid = other_rid
                    break
            if target_pid:
                break

        if not target_pid or target_rid is None:
            return [
                HygieneSuggestion(
                    action_type="consolidate",
                    primary_player_ids=[a, b],
                    primary_player_names=[
                        self._player_name(a),
                        self._player_name(b),
                    ],
                    reasoning=(
                        f"Package {self._player_name(a)} + {self._player_name(b)} -> "
                        "target upgrade on the trade market (no specific counterparty found)."
                    ),
                    direction_fit_score=0.55,
                )
            ][:1]

        na, nb = self._player_name(a), self._player_name(b)
        tx = self._player_name(target_pid)
        mgr = name_by_rid.get(target_rid, "Manager")
        req = TradeRequest(
            league_id=league_id,
            user_roster_id=roster_id,
            counterparty_roster_id=target_rid,
            user_sends=[
                TradeAsset(asset_type="player", player_id=a),
                TradeAsset(asset_type="player", player_id=b),
            ],
            user_receives=[TradeAsset(asset_type="player", player_id=target_pid)],
            include_package=True,
        )
        try:
            evaluation = self._trade_engine.evaluate(req)
            pkg = self._package_builder.build(req, evaluation)
        except Exception:
            pkg = None

        reasoning = (
            f"Package {na} + {nb} -> target {tx} from {mgr}."
        )
        if pkg is None:
            reasoning += " (Package builder unavailable; still a recommended trade shape.)"

        return [
            HygieneSuggestion(
                action_type="consolidate",
                primary_player_ids=[a, b],
                primary_player_names=[na, nb],
                target_player_id=target_pid,
                target_player_name=tx,
                counterparty_roster_id=target_rid,
                counterparty_name=mgr,
                reasoning=reasoning,
                direction_fit_score=0.65,
            )
        ]

    def _row_lens(
        self, league_id: str, roster_id: int, player_id: str
    ) -> float:
        row = self._conn.execute(
            """
            SELECT lens_direction
            FROM player_values
            WHERE league_id = ? AND roster_id = ? AND player_id = ?
            """,
            [league_id, roster_id, player_id],
        ).fetchone()
        if row is None:
            return 0.0
        return float(row[0] or 0.0)

    def _player_name(self, player_id: str) -> str:
        row = self._conn.execute(
            "SELECT COALESCE(full_name, player_id) FROM players WHERE player_id = ?",
            [player_id],
        ).fetchone()
        return str(row[0]) if row else player_id
