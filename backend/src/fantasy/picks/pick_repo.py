"""PickRepo: DuckDB data access layer for Phase 6 pick valuation.

Reads picks, standings, team_directions, and trades tables.
Writes computed values to pick_values table.
"""

from __future__ import annotations

import json

import duckdb

from fantasy.picks.constants import (
    DIRECTION_DEMAND_MAP,
    DIRECTION_DEMAND_WEIGHT,
    HISTORY_DEMAND_WEIGHT,
    DEMAND_HISTORY_SIGMOID_K,
    DEMAND_HISTORY_SIGMOID_CENTER,
    MIN_TRADE_EVIDENCE_THRESHOLD,
    NEUTRAL_REBUILDER_RATIO,
    TOTAL_SEASON_GAMES,
)
from fantasy.picks.models import (
    LeaguePickContext,
    PickValue,
    TeamStandingsRow,
)
from fantasy.trade.models import TradeAsset


def _sigmoid(k: float, center: float, x: float) -> float:
    """Logistic sigmoid normalized to [0.0, 1.0]."""
    import math
    return 1.0 / (1.0 + math.exp(-k * (x - center)))


class PickRepo:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn

    def get_standings(self, roster_id: int, league_id: str) -> TeamStandingsRow:
        """Return standings row with last-4-game trend window.

        Guards against remaining_games=0 (Pitfall 1).
        Falls back to neutral (0.5 win_pct, 0 recent_wins) if row missing.
        """
        # Try to get standings with weekly trend using window function
        row = self._conn.execute(
            """
            SELECT
                s.roster_id,
                s.wins,
                s.losses,
                s.wins::FLOAT / NULLIF(s.wins + s.losses, 0) AS win_pct,
                GREATEST(0, (? - s.wins - s.losses)) AS remaining_games,
                s.wins + s.losses AS total_games
            FROM standings s
            WHERE s.league_id = ?
              AND s.roster_id = ?
            LIMIT 1
            """,
            [TOTAL_SEASON_GAMES, league_id, roster_id],
        ).fetchone()

        if row is None:
            # Fallback to neutral — no standings data for this manager
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

        roster_id_val = int(row[0])
        wins = int(row[1])
        losses = int(row[2])
        win_pct = float(row[3]) if row[3] is not None else 0.5
        remaining_games = int(row[4])
        total_games = int(row[5])

        # Try to fetch recent_wins from weekly_results if table exists
        recent_wins = 0
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
                recent_wins = int(recent_row[0])
        except duckdb.Error:
            # weekly_results table may not exist — use 0 as fallback
            recent_wins = 0

        return TeamStandingsRow(
            roster_id=roster_id_val,
            wins=wins,
            losses=losses,
            win_pct=win_pct,
            remaining_games=remaining_games,
            recent_wins=recent_wins,
            total_games=total_games,
            draft_in_progress=False,
        )

    def get_league_pick_context(self, league_id: str) -> LeaguePickContext:
        """Return league-level pick context with rebuilder count.

        Counts teams whose direction label is hard_rebuild, elite_value_accumulation,
        or one_year_punt. Falls back to neutral ratio if no team_directions data (Pitfall 3).
        """
        row = self._conn.execute(
            """
            SELECT
                league_id,
                COUNT(*) FILTER (
                    WHERE primary_label IN ('hard_rebuild', 'elite_value_accumulation', 'one_year_punt')
                ) AS rebuilder_count,
                COUNT(*) AS total_teams,
                COUNT(*) FILTER (
                    WHERE primary_label IN ('hard_rebuild', 'elite_value_accumulation', 'one_year_punt')
                )::FLOAT / NULLIF(COUNT(*), 0) AS rebuilder_ratio
            FROM team_directions
            WHERE league_id = ?
            GROUP BY league_id
            """,
            [league_id],
        ).fetchone()

        if row is None:
            # No team_directions data — use neutral ratio fallback (Pitfall 3)
            # Estimate league size from rosters table
            league_size_row = self._conn.execute(
                "SELECT COUNT(*) FROM rosters WHERE league_id = ? LIMIT 1",
                [league_id],
            ).fetchone()
            league_size = int(league_size_row[0]) if league_size_row else 12
            rebuilder_count = int(round(NEUTRAL_REBUILDER_RATIO * league_size))
            return LeaguePickContext(
                league_id=league_id,
                league_size=max(2, league_size),
                rebuilder_count=rebuilder_count,
                rebuilder_ratio=NEUTRAL_REBUILDER_RATIO,
                total_teams=max(1, league_size),
            )

        total_teams = int(row[2])
        rebuilder_count = int(row[1])
        rebuilder_ratio = float(row[3]) if row[3] is not None else NEUTRAL_REBUILDER_RATIO

        return LeaguePickContext(
            league_id=league_id,
            league_size=max(2, total_teams),
            rebuilder_count=rebuilder_count,
            rebuilder_ratio=rebuilder_ratio,
            total_teams=max(1, total_teams),
        )

    def get_manager_demand_factor(self, roster_id: int, league_id: str) -> float:
        """Compute per-manager demand factor from direction label + trade history.

        Returns float in [0.0, 1.0]. Falls back to 0.5 (neutral) if no data (Pitfall 3).
        Suppresses history signal below MIN_TRADE_EVIDENCE_THRESHOLD (D-09).
        """
        # Signal 1: direction label demand score
        direction_demand_score = 0.5  # neutral default
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
            pass

        # Signal 2: pick reception rate from trade history
        demand_from_history = 0.5  # neutral default (will be suppressed if low evidence)
        history_weight = 0.0  # will be set to HISTORY_DEMAND_WEIGHT if evidence threshold met
        try:
            hist_row = self._conn.execute(
                """
                SELECT
                    COUNT(*) FILTER (WHERE pick_received = TRUE) AS picks_received_count,
                    COUNT(*) AS total_trades,
                    COUNT(*) FILTER (WHERE pick_received = TRUE)::FLOAT
                        / NULLIF(COUNT(*), 0) AS pick_reception_rate
                FROM (
                    SELECT
                        t.id,
                        MAX(CASE WHEN ta.asset_type = 'pick' AND ta.direction = 'received'
                            THEN 1 ELSE 0 END) = 1 AS pick_received
                    FROM trades t
                    JOIN trade_assets ta ON ta.trade_id = t.id
                    WHERE t.league_id = ?
                    GROUP BY t.id
                ) sub
                JOIN trades t2 ON t2.id = sub.id AND t2.receiver_roster_id = ?
                """,
                [league_id, roster_id],
            ).fetchone()

            if hist_row and hist_row[1] is not None:
                total_trades = int(hist_row[1])
                if total_trades >= MIN_TRADE_EVIDENCE_THRESHOLD:
                    pick_reception_rate = float(hist_row[2]) if hist_row[2] is not None else 0.4
                    demand_from_history = _sigmoid(
                        DEMAND_HISTORY_SIGMOID_K,
                        DEMAND_HISTORY_SIGMOID_CENTER,
                        pick_reception_rate,
                    )
                    history_weight = HISTORY_DEMAND_WEIGHT
                # Below threshold: history signal suppressed — direction label only
        except duckdb.Error:
            pass

        # Combine signals — re-normalize when history is suppressed
        if history_weight == 0.0:
            return direction_demand_score
        else:
            direction_weight = DIRECTION_DEMAND_WEIGHT
            return direction_weight * direction_demand_score + history_weight * demand_from_history

    def get_all_picks(self, league_id: str) -> list[TradeAsset]:
        """Return all future picks owned in the league from the picks table."""
        rows = self._conn.execute(
            """
            SELECT owner_roster_id, original_roster_id, pick_year, round
            FROM picks
            WHERE league_id = ?
            ORDER BY pick_year, round, owner_roster_id
            """,
            [league_id],
        ).fetchall()

        result: list[TradeAsset] = []
        for row in rows:
            result.append(
                TradeAsset(
                    asset_type="pick",
                    pick_owner_roster_id=int(row[0]),
                    pick_year=int(row[2]),
                    pick_round=int(row[3]),
                )
            )
        return result

    def save_pick_values(self, league_id: str, values: list[PickValue]) -> None:
        """Upsert computed pick values into pick_values table.

        Uses UNIQUE constraint on (league_id, pick_owner_roster_id, pick_year, pick_round)
        via INSERT OR REPLACE to handle repeated computations.
        """
        for pv in values:
            pick = pv.pick
            self._conn.execute(
                """
                INSERT OR REPLACE INTO pick_values (
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
                    computation_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
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
                    json.dumps({}),
                ],
            )
