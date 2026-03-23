"""PickRepo: DuckDB data access layer for dynamic pick valuation.

Reads league settings, standings, traded pick ownership, transactions, and
Phase 7 rookie board cache. Writes computed values to pick_values.
"""

from __future__ import annotations

import json
from typing import Any

import duckdb

from fantasy.picks.constants import (
    DEMAND_HISTORY_SIGMOID_CENTER,
    DEMAND_HISTORY_SIGMOID_K,
    DIRECTION_DEMAND_MAP,
    HISTORY_DEMAND_WEIGHT,
    MIN_TRADE_EVIDENCE_THRESHOLD,
    NEUTRAL_REBUILDER_RATIO,
    TOTAL_SEASON_GAMES,
)
from fantasy.picks.models import LeaguePickContext, PickValue, TeamStandingsRow
from fantasy.trade.models import TradeAsset


def _loads(raw: str | None, fallback: Any) -> Any:
    if raw is None:
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


def _sigmoid(k: float, center: float, x: float) -> float:
    """Logistic sigmoid normalized to [0.0, 1.0]."""
    import math

    return 1.0 / (1.0 + math.exp(-k * (x - center)))


class PickRepo:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn

    def get_current_season(self, league_id: str) -> int:
        row = self._conn.execute(
            """
            SELECT season
            FROM leagues
            WHERE league_id = ?
            LIMIT 1
            """,
            [league_id],
        ).fetchone()
        if row is None or row[0] is None:
            return 2026
        return int(row[0])

    def get_confirmed_slot(
        self, league_id: str, roster_id: int, pick_year: int
    ) -> int | None:
        """Return confirmed draft slot for a roster in a given season, or None if not known.

        Prefers complete drafts > drafting > pre_draft when multiple entries exist.
        """
        row = self._conn.execute(
            """
            SELECT confirmed_slot
            FROM draft_slots
            WHERE league_id = ? AND roster_id = ? AND season = ?
            ORDER BY
                CASE status
                    WHEN 'complete'   THEN 0
                    WHEN 'drafting'   THEN 1
                    WHEN 'paused'     THEN 2
                    ELSE 3
                END
            LIMIT 1
            """,
            [league_id, roster_id, pick_year],
        ).fetchone()
        return int(row[0]) if row is not None else None

    def get_standings(self, roster_id: int, league_id: str) -> TeamStandingsRow:
        """Return standings row with safe fallbacks.

        Guards against missing standings rows and missing weekly trend data.
        """

        row = self._conn.execute(
            """
            SELECT
                roster_id,
                wins,
                losses,
                wins::DOUBLE / NULLIF(wins + losses, 0) AS win_pct,
                GREATEST(0, (? - wins - losses)) AS remaining_games,
                wins + losses AS total_games
            FROM standings
            WHERE league_id = ?
              AND roster_id = ?
            LIMIT 1
            """,
            [TOTAL_SEASON_GAMES, league_id, roster_id],
        ).fetchone()

        if row is None:
            return TeamStandingsRow(
                roster_id=roster_id,
                wins=0,
                losses=0,
                win_pct=0.5,
                remaining_games=TOTAL_SEASON_GAMES,
                recent_wins=0,
                total_games=0,
                draft_in_progress=False,
            )

        recent_wins = 0
        total_games = int(row[5] or 0)
        try:
            recent_row = self._conn.execute(
                """
                SELECT COUNT(*) AS recent_wins
                FROM weekly_results
                WHERE league_id = ?
                  AND roster_id = ?
                  AND outcome = 'win'
                  AND week >= (? - 3)
                """,
                [league_id, roster_id, total_games],
            ).fetchone()
            if recent_row is not None:
                recent_wins = int(recent_row[0] or 0)
        except duckdb.Error:
            recent_wins = 0

        return TeamStandingsRow(
            roster_id=int(row[0]),
            wins=int(row[1]),
            losses=int(row[2]),
            win_pct=float(row[3]) if row[3] is not None else 0.5,
            remaining_games=int(row[4] or 0),
            recent_wins=recent_wins,
            total_games=total_games,
            draft_in_progress=False,
        )

    def get_league_pick_context(self, league_id: str) -> LeaguePickContext:
        """Return league-level pick context with rebuilder count."""

        league_size_row = self._conn.execute(
            "SELECT COUNT(*) FROM rosters WHERE league_id = ?",
            [league_id],
        ).fetchone()
        league_size = max(2, int(league_size_row[0] or 0)) if league_size_row else 12

        row = self._conn.execute(
            """
            SELECT
                COUNT(*) FILTER (
                    WHERE primary_label IN ('hard_rebuild', 'elite_value_accumulation', 'one_year_punt')
                ) AS rebuilder_count,
                COUNT(*) AS total_teams
            FROM team_directions
            WHERE league_id = ?
            """,
            [league_id],
        ).fetchone()

        if row is None or int(row[1] or 0) == 0:
            rebuilder_count = int(round(NEUTRAL_REBUILDER_RATIO * league_size))
            return LeaguePickContext(
                league_id=league_id,
                league_size=league_size,
                rebuilder_count=rebuilder_count,
                rebuilder_ratio=NEUTRAL_REBUILDER_RATIO,
                total_teams=league_size,
            )

        total_teams = max(1, int(row[1] or 0))
        rebuilder_count = int(row[0] or 0)
        return LeaguePickContext(
            league_id=league_id,
            league_size=league_size,
            rebuilder_count=rebuilder_count,
            rebuilder_ratio=rebuilder_count / total_teams,
            total_teams=total_teams,
        )

    def get_manager_demand_factor(self, roster_id: int, league_id: str) -> float:
        """Compute per-manager pick demand from direction plus trade history."""

        direction_demand_score = 0.5
        try:
            dir_row = self._conn.execute(
                """
                SELECT primary_label
                FROM team_directions
                WHERE league_id = ?
                  AND roster_id = ?
                LIMIT 1
                """,
                [league_id, roster_id],
            ).fetchone()
            if dir_row and dir_row[0]:
                direction_demand_score = DIRECTION_DEMAND_MAP.get(str(dir_row[0]), 0.5)
        except duckdb.Error:
            direction_demand_score = 0.5

        try:
            rows = self._conn.execute(
                """
                SELECT roster_ids, draft_picks
                FROM transactions
                WHERE league_id = ?
                  AND type = 'trade'
                """,
                [league_id],
            ).fetchall()
        except duckdb.Error:
            return direction_demand_score

        total_trades = 0
        trades_with_received_pick = 0
        for roster_ids_raw, draft_picks_raw in rows:
            roster_ids = [int(value) for value in _loads(roster_ids_raw, [])]
            if roster_id not in roster_ids:
                continue
            total_trades += 1
            draft_picks = _loads(draft_picks_raw, [])
            if any(int(pick.get("owner_id", -1)) == roster_id for pick in draft_picks):
                trades_with_received_pick += 1

        if total_trades < MIN_TRADE_EVIDENCE_THRESHOLD:
            return direction_demand_score

        pick_reception_rate = trades_with_received_pick / max(total_trades, 1)
        demand_from_history = _sigmoid(
            DEMAND_HISTORY_SIGMOID_K,
            DEMAND_HISTORY_SIGMOID_CENTER,
            pick_reception_rate,
        )
        direction_weight = 1.0 - HISTORY_DEMAND_WEIGHT
        return direction_weight * direction_demand_score + HISTORY_DEMAND_WEIGHT * demand_from_history

    def _get_pick_inventory_rows(self, league_id: str) -> list[dict[str, Any]]:
        owner_rows = self._conn.execute(
            """
            SELECT roster_id, owner_id, owner_display_name
            FROM rosters
            WHERE league_id = ?
            ORDER BY roster_id
            """,
            [league_id],
        ).fetchall()
        if not owner_rows:
            return []

        owner_name_by_roster = {
            int(row[0]): str(row[2] or row[1] or f"Roster {int(row[0])}") for row in owner_rows
        }
        original_owner_ids = sorted(owner_name_by_roster)

        league_row = self._conn.execute(
            """
            SELECT season, settings_blob
            FROM leagues
            WHERE league_id = ?
            LIMIT 1
            """,
            [league_id],
        ).fetchone()
        if league_row is None:
            return []

        current_season = int(league_row[0] or 2026)
        league_settings = _loads(league_row[1], {})
        draft_rounds = max(int(league_settings.get("draft_rounds", 3) or 3), 1)
        future_seasons = [current_season + offset for offset in range(3)]

        traded_rows = self._conn.execute(
            """
            SELECT roster_id, owner_id, season, round
            FROM traded_picks
            WHERE league_id = ?
              AND CAST(season AS INTEGER) >= ?
            """,
            [league_id, current_season],
        ).fetchall()
        current_owner_by_pick = {
            (int(row[2]), int(row[3]), int(row[0])): int(row[1])
            for row in traded_rows
        }

        slot_by_pick = {
            (int(row[0]), int(row[1]), int(row[2])): float(row[3])
            for row in self._conn.execute(
                """
                SELECT pick_owner_roster_id, pick_year, pick_round, expected_draft_slot
                FROM pick_values
                WHERE league_id = ?
                """,
                [league_id],
            ).fetchall()
        }

        confirmed_by_roster_season: dict[tuple[int, int], int] = {}
        for row in self._conn.execute(
            """
            SELECT roster_id, season, confirmed_slot
            FROM draft_slots
            WHERE league_id = ?
            ORDER BY
                CASE status
                    WHEN 'complete'  THEN 0
                    WHEN 'drafting'  THEN 1
                    WHEN 'paused'    THEN 2
                    ELSE 3
                END,
                roster_id
            """,
            [league_id],
        ).fetchall():
            key = (int(row[0]), int(row[1]))
            if key not in confirmed_by_roster_season:
                confirmed_by_roster_season[key] = int(row[2])

        inventory: list[dict[str, Any]] = []
        for original_owner_id in original_owner_ids:
            for pick_year in future_seasons:
                for round_no in range(1, draft_rounds + 1):
                    current_owner_id = current_owner_by_pick.get(
                        (pick_year, round_no, original_owner_id),
                        original_owner_id,
                    )
                    confirmed = confirmed_by_roster_season.get((original_owner_id, pick_year))
                    if confirmed is not None:
                        projected_slot = f"{round_no}.{confirmed:02d}"
                    else:
                        raw_slot = slot_by_pick.get((original_owner_id, pick_year, round_no))
                        projected_slot = (
                            f"~{round_no}.{int(round(raw_slot)):02d}"
                            if raw_slot is not None
                            else f"{round_no}.mid"
                        )
                    inventory.append(
                        {
                            "original_owner_id": original_owner_id,
                            "current_owner_id": current_owner_id,
                            "pick_year": pick_year,
                            "round": round_no,
                            "original_owner_name": owner_name_by_roster.get(
                                original_owner_id,
                                f"Roster {original_owner_id}",
                            ),
                            "current_owner_name": owner_name_by_roster.get(
                                current_owner_id,
                                f"Roster {current_owner_id}",
                            ),
                            "projected_slot": projected_slot,
                        }
                    )
        inventory.sort(
            key=lambda item: (
                item["pick_year"],
                item["round"],
                item["current_owner_id"],
                item["original_owner_id"],
            )
        )
        return inventory

    def get_all_picks(
        self,
        league_id: str,
        current_owner_roster_id: int | None = None,
    ) -> list[TradeAsset]:
        """Return all future picks for the league.

        Pick identity is keyed by original owner roster id, year, and round.
        """

        return [
            TradeAsset(
                asset_type="pick",
                pick_owner_roster_id=int(row["original_owner_id"]),
                pick_year=int(row["pick_year"]),
                pick_round=int(row["round"]),
                projected_slot=str(row["projected_slot"]),
            )
            for row in self._get_pick_inventory_rows(league_id)
            if current_owner_roster_id is None
            or int(row["current_owner_id"]) == current_owner_roster_id
        ]

    def has_pick(
        self,
        league_id: str,
        owner_roster_id: int,
        pick_year: int,
        pick_round: int,
    ) -> bool:
        return any(
            row["original_owner_id"] == owner_roster_id
            and row["pick_year"] == pick_year
            and row["round"] == pick_round
            for row in self._get_pick_inventory_rows(league_id)
        )

    def get_pick_owner_name(self, league_id: str, owner_roster_id: int) -> str | None:
        row = self._conn.execute(
            """
            SELECT owner_display_name, owner_id
            FROM rosters
            WHERE league_id = ?
              AND roster_id = ?
            LIMIT 1
            """,
            [league_id, owner_roster_id],
        ).fetchone()
        if row is None:
            return None
        return str(row[0] or row[1] or f"Roster {owner_roster_id}")

    def get_class_strength_signal(self, league_id: str) -> float | None:
        try:
            row = self._conn.execute(
                """
                SELECT class_strength_signal
                FROM rookie_board_cache
                WHERE league_id = ?
                ORDER BY computed_at DESC
                LIMIT 1
                """,
                [league_id],
            ).fetchone()
        except duckdb.Error:
            return None

        if row is None or row[0] is None:
            return None
        return float(row[0])

    def save_pick_values(self, league_id: str, values: list[PickValue]) -> None:
        """Upsert computed pick values into pick_values."""

        for pv in values:
            pick = pv.pick
            next_id_row = self._conn.execute(
                "SELECT COALESCE(MAX(id), 0) + 1 FROM pick_values"
            ).fetchone()
            next_id = int(next_id_row[0] or 1) if next_id_row else 1
            self._conn.execute(
                """
                DELETE FROM pick_values
                WHERE league_id = ?
                  AND pick_owner_roster_id = ?
                  AND pick_year = ?
                  AND pick_round = ?
                """,
                [
                    league_id,
                    pick.pick_owner_roster_id,
                    pick.pick_year,
                    pick.pick_round,
                ],
            )
            self._conn.execute(
                """
                INSERT INTO pick_values (
                    id,
                    league_id,
                    pick_owner_roster_id,
                    pick_year,
                    pick_round,
                    computed_at,
                    expected_draft_slot,
                    base_value,
                    timed_value,
                    league_adjusted_value,
                    demand_adjusted_value,
                    timing_label,
                    timing_reasoning,
                    class_strength_signal,
                    years_out,
                    computation_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    next_id,
                    league_id,
                    pick.pick_owner_roster_id,
                    pick.pick_year,
                    pick.pick_round,
                    pv.computed_at.isoformat(),
                    pv.expected_draft_slot,
                    pv.base_value,
                    pv.timed_value,
                    pv.league_adjusted_value,
                    pv.demand_adjusted_value,
                    pv.timing_label.value,
                    pv.timing_reasoning,
                    pv.class_strength_signal,
                    pv.years_out,
                    json.dumps({}),
                ],
            )
