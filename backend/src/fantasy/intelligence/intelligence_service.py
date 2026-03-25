from __future__ import annotations

import json
from typing import Any

import duckdb

from fantasy.intelligence.constants import CONTENDER_DIRECTION_LABELS
from fantasy.intelligence.direction_engine import DirectionEngine
from fantasy.intelligence.models import DirectionResult, PlayerValue, TeamScorecard
from fantasy.intelligence.scorecard_engine import ScorecardEngine
from fantasy.intelligence.valuation_engine import ValuationEngine
from fantasy.lineup.constants import TITLE_WINDOW_FRAGILITY_BOOST
from fantasy.lineup.hygiene_engine import HygieneEngine
from fantasy.lineup.lineup_engine import LineupEngine
from fantasy.lineup.lineup_repo import LineupRepo
from fantasy.lineup.models import HygieneResult, LineupResult


class IntelligenceService:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn
        self._scorecard_engine = ScorecardEngine(conn)
        self._direction_engine = DirectionEngine()
        self._valuation_engine = ValuationEngine(conn)
        self._lineup_engine = LineupEngine(conn)
        self._hygiene_engine = HygieneEngine(conn)
        self._lineup_repo = LineupRepo(conn)

    def compute_league(self, league_id: str) -> dict[str, Any]:
        scorecards = self._scorecard_engine.compute_all(league_id)
        directions = {
            roster_id: self._direction_engine.classify(scorecard)
            for roster_id, scorecard in scorecards.items()
        }

        all_inputs = {
            roster_id: self._scorecard_engine._apply_corrections(
                self._scorecard_engine._gather_inputs(league_id, roster_id),
                league_id,
                roster_id,
            )
            for roster_id in scorecards.keys()
        }

        lineup_results = self._lineup_engine.compute_all(
            league_id, all_inputs, scorecards
        )

        for roster_id, lineup_result in lineup_results.items():
            direction = directions[roster_id]
            if (
                lineup_result.title_window_label == "Outside Window"
                and direction.primary_label in CONTENDER_DIRECTION_LABELS
            ):
                adjusted_scorecard = scorecards[roster_id].model_copy()
                adjusted_scorecard.fragility = min(
                    1.0,
                    float(adjusted_scorecard.fragility) + TITLE_WINDOW_FRAGILITY_BOOST,
                )
                adjusted_direction = self._direction_engine.classify(adjusted_scorecard)
                if adjusted_direction.primary_label != direction.primary_label:
                    directions[roster_id] = adjusted_direction

        values: dict[int, dict[str, PlayerValue]] = {}
        for roster_id, direction in directions.items():
            values[roster_id] = self._valuation_engine.compute_all(
                league_id, roster_id, direction.primary_label
            )

        hygiene_results: dict[int, HygieneResult] = {}
        for roster_id, inp in all_inputs.items():
            hygiene_results[roster_id] = self._hygiene_engine.compute(
                league_id,
                roster_id,
                inp,
                directions[roster_id].primary_label,
                all_inputs,
            )

        for roster_id, result in lineup_results.items():
            self._lineup_repo.save_lineup_result(result)
        for roster_id, result in hygiene_results.items():
            self._lineup_repo.save_hygiene_result(result)

        self._persist_scorecards(scorecards)
        self._persist_directions(league_id, directions)
        self._persist_values(values)
        return {
            "scorecards": scorecards,
            "directions": directions,
            "values": values,
            "lineup": lineup_results,
            "hygiene": hygiene_results,
        }

    def get_scorecard(self, league_id: str, roster_id: int) -> TeamScorecard:
        row = self._conn.execute(
            """
            SELECT league_id, roster_id, CAST(computed_at AS VARCHAR), win_now, future_value, depth,
                   pick_capital, flexibility, fragility, age_risk, liquidity,
                   positional_insulation, composite, computation_json
            FROM team_scorecards
            WHERE league_id = ? AND roster_id = ?
            LIMIT 1
            """,
            [league_id, roster_id],
        ).fetchone()
        if row is None:
            self.compute_league(league_id)
            row = self._conn.execute(
                """
                SELECT league_id, roster_id, CAST(computed_at AS VARCHAR), win_now, future_value, depth,
                       pick_capital, flexibility, fragility, age_risk, liquidity,
                       positional_insulation, composite, computation_json
                FROM team_scorecards
                WHERE league_id = ? AND roster_id = ?
                LIMIT 1
                """,
                [league_id, roster_id],
            ).fetchone()
        if row is None:
            raise ValueError(f"scorecard not found: {league_id}/{roster_id}")
        return TeamScorecard(
            league_id=row[0],
            roster_id=int(row[1]),
            computed_at=row[2],
            win_now=float(row[3]),
            future_value=float(row[4]),
            depth=float(row[5]),
            pick_capital=float(row[6]),
            flexibility=float(row[7]),
            fragility=float(row[8]),
            age_risk=float(row[9]),
            liquidity=float(row[10]),
            positional_insulation=float(row[11]),
            composite=float(row[12]),
            computation_json=row[13],
        )

    def get_direction(self, league_id: str, roster_id: int) -> DirectionResult:
        row = self._conn.execute(
            """
            SELECT primary_label, confidence, reasoning, alternates_json, delta_json,
                   approved_moves, discouraged_moves
            FROM team_directions
            WHERE league_id = ? AND roster_id = ?
            LIMIT 1
            """,
            [league_id, roster_id],
        ).fetchone()
        if row is None:
            self.compute_league(league_id)
            row = self._conn.execute(
                """
                SELECT primary_label, confidence, reasoning, alternates_json, delta_json,
                       approved_moves, discouraged_moves
                FROM team_directions
                WHERE league_id = ? AND roster_id = ?
                LIMIT 1
                """,
                [league_id, roster_id],
            ).fetchone()
        if row is None:
            raise ValueError(f"direction not found: {league_id}/{roster_id}")
        return DirectionResult(
            primary_label=row[0],
            confidence=float(row[1]),
            reasoning=row[2],
            alternates=json.loads(row[3]),
            delta=json.loads(row[4]),
            approved_moves=json.loads(row[5]),
            discouraged_moves=json.loads(row[6]),
        )

    def get_player_value(self, league_id: str, roster_id: int, player_id: str) -> PlayerValue:
        row = self._conn.execute(
            """
            SELECT league_id, roster_id, player_id, CAST(computed_at AS VARCHAR),
                   comp_current_production, comp_short_term, comp_role_stability,
                   comp_age_curve, comp_insulation, comp_market_liquidity,
                   comp_positional_scarcity, comp_fragility, comp_ceiling, comp_floor,
                   comp_rerollability, comp_contract, lens_production, lens_market,
                   lens_insulation, lens_team_fit, lens_direction
            FROM player_values
            WHERE league_id = ? AND roster_id = ? AND player_id = ?
            LIMIT 1
            """,
            [league_id, roster_id, player_id],
        ).fetchone()
        if row is None:
            self.compute_league(league_id)
            row = self._conn.execute(
                """
                SELECT league_id, roster_id, player_id, CAST(computed_at AS VARCHAR),
                       comp_current_production, comp_short_term, comp_role_stability,
                       comp_age_curve, comp_insulation, comp_market_liquidity,
                       comp_positional_scarcity, comp_fragility, comp_ceiling, comp_floor,
                       comp_rerollability, comp_contract, lens_production, lens_market,
                       lens_insulation, lens_team_fit, lens_direction
                FROM player_values
                WHERE league_id = ? AND roster_id = ? AND player_id = ?
                LIMIT 1
                """,
                [league_id, roster_id, player_id],
            ).fetchone()
        if row is None:
            raise ValueError(f"player value not found: {league_id}/{roster_id}/{player_id}")
        return PlayerValue(
            league_id=row[0],
            roster_id=int(row[1]),
            player_id=row[2],
            computed_at=row[3],
            comp_current_production=row[4],
            comp_short_term=row[5],
            comp_role_stability=row[6],
            comp_age_curve=row[7],
            comp_insulation=row[8],
            comp_market_liquidity=row[9],
            comp_positional_scarcity=row[10],
            comp_fragility=row[11],
            comp_ceiling=row[12],
            comp_floor=row[13],
            comp_rerollability=row[14],
            comp_contract=row[15],
            lens_production=row[16],
            lens_market=row[17],
            lens_insulation=row[18],
            lens_team_fit=row[19],
            lens_direction=row[20],
        )

    def get_lineup_result(self, league_id: str, roster_id: int) -> LineupResult:
        cached = self._lineup_repo.get_lineup_result(league_id, roster_id)
        if cached is not None:
            return cached
        self.compute_league(league_id)
        refreshed = self._lineup_repo.get_lineup_result(league_id, roster_id)
        if refreshed is None:
            raise ValueError(f"lineup result not found: {league_id}/{roster_id}")
        return refreshed

    def get_hygiene_result(self, league_id: str, roster_id: int) -> HygieneResult:
        cached = self._lineup_repo.get_hygiene_result(league_id, roster_id)
        if cached is not None:
            return cached
        self.compute_league(league_id)
        refreshed = self._lineup_repo.get_hygiene_result(league_id, roster_id)
        if refreshed is None:
            raise ValueError(f"hygiene result not found: {league_id}/{roster_id}")
        return refreshed

    def _next_id(self, table: str) -> int:
        return int(self._conn.execute(f"SELECT COALESCE(MAX(id), 0) + 1 FROM {table}").fetchone()[0])

    def _persist_scorecards(self, scorecards: dict[int, TeamScorecard]) -> None:
        for roster_id, scorecard in scorecards.items():
            existing = self._conn.execute(
                "SELECT id FROM team_scorecards WHERE league_id = ? AND roster_id = ?",
                [scorecard.league_id, roster_id],
            ).fetchone()
            row_id = int(existing[0]) if existing else self._next_id("team_scorecards")
            self._conn.execute(
                """
                INSERT INTO team_scorecards (
                    id, league_id, roster_id, win_now, future_value, depth,
                    pick_capital, flexibility, fragility, age_risk, liquidity,
                    positional_insulation, composite, computation_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (league_id, roster_id) DO UPDATE SET
                    win_now = EXCLUDED.win_now,
                    future_value = EXCLUDED.future_value,
                    depth = EXCLUDED.depth,
                    pick_capital = EXCLUDED.pick_capital,
                    flexibility = EXCLUDED.flexibility,
                    fragility = EXCLUDED.fragility,
                    age_risk = EXCLUDED.age_risk,
                    liquidity = EXCLUDED.liquidity,
                    positional_insulation = EXCLUDED.positional_insulation,
                    composite = EXCLUDED.composite,
                    computation_json = EXCLUDED.computation_json
                """,
                [
                    row_id,
                    scorecard.league_id,
                    roster_id,
                    scorecard.win_now,
                    scorecard.future_value,
                    scorecard.depth,
                    scorecard.pick_capital,
                    scorecard.flexibility,
                    scorecard.fragility,
                    scorecard.age_risk,
                    scorecard.liquidity,
                    scorecard.positional_insulation,
                    scorecard.composite,
                    scorecard.computation_json,
                ],
            )

    def _persist_directions(self, league_id: str, directions: dict[int, DirectionResult]) -> None:
        for roster_id, direction in directions.items():
            existing = self._conn.execute(
                "SELECT id FROM team_directions WHERE league_id = ? AND roster_id = ?",
                [league_id, roster_id],
            ).fetchone()
            row_id = int(existing[0]) if existing else self._next_id("team_directions")
            self._conn.execute(
                """
                INSERT INTO team_directions (
                    id, league_id, roster_id, primary_label, confidence, reasoning,
                    alternates_json, delta_json, approved_moves, discouraged_moves
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (league_id, roster_id) DO UPDATE SET
                    primary_label = EXCLUDED.primary_label,
                    confidence = EXCLUDED.confidence,
                    reasoning = EXCLUDED.reasoning,
                    alternates_json = EXCLUDED.alternates_json,
                    delta_json = EXCLUDED.delta_json,
                    approved_moves = EXCLUDED.approved_moves,
                    discouraged_moves = EXCLUDED.discouraged_moves
                """,
                [
                    row_id,
                    league_id,
                    roster_id,
                    direction.primary_label,
                    direction.confidence,
                    direction.reasoning,
                    json.dumps(direction.alternates, separators=(",", ":")),
                    json.dumps(direction.delta, separators=(",", ":")),
                    json.dumps(direction.approved_moves, separators=(",", ":")),
                    json.dumps(direction.discouraged_moves, separators=(",", ":")),
                ],
            )

    def _persist_values(self, values: dict[int, dict[str, PlayerValue]]) -> None:
        for roster_id, roster_values in values.items():
            for player_id, value in roster_values.items():
                existing = self._conn.execute(
                    """
                    SELECT id
                    FROM player_values
                    WHERE league_id = ? AND roster_id = ? AND player_id = ?
                    """,
                    [value.league_id, roster_id, player_id],
                ).fetchone()
                row_id = int(existing[0]) if existing else self._next_id("player_values")
                self._conn.execute(
                    """
                    INSERT INTO player_values (
                        id, league_id, roster_id, player_id,
                        comp_current_production, comp_short_term, comp_role_stability,
                        comp_age_curve, comp_insulation, comp_market_liquidity,
                        comp_positional_scarcity, comp_fragility, comp_ceiling,
                        comp_floor, comp_rerollability, comp_contract,
                        lens_production, lens_market, lens_insulation, lens_team_fit, lens_direction
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (league_id, roster_id, player_id) DO UPDATE SET
                        comp_current_production = EXCLUDED.comp_current_production,
                        comp_short_term = EXCLUDED.comp_short_term,
                        comp_role_stability = EXCLUDED.comp_role_stability,
                        comp_age_curve = EXCLUDED.comp_age_curve,
                        comp_insulation = EXCLUDED.comp_insulation,
                        comp_market_liquidity = EXCLUDED.comp_market_liquidity,
                        comp_positional_scarcity = EXCLUDED.comp_positional_scarcity,
                        comp_fragility = EXCLUDED.comp_fragility,
                        comp_ceiling = EXCLUDED.comp_ceiling,
                        comp_floor = EXCLUDED.comp_floor,
                        comp_rerollability = EXCLUDED.comp_rerollability,
                        comp_contract = EXCLUDED.comp_contract,
                        lens_production = EXCLUDED.lens_production,
                        lens_market = EXCLUDED.lens_market,
                        lens_insulation = EXCLUDED.lens_insulation,
                        lens_team_fit = EXCLUDED.lens_team_fit,
                        lens_direction = EXCLUDED.lens_direction
                    """,
                    [
                        row_id,
                        value.league_id,
                        roster_id,
                        player_id,
                        value.comp_current_production,
                        value.comp_short_term,
                        value.comp_role_stability,
                        value.comp_age_curve,
                        value.comp_insulation,
                        value.comp_market_liquidity,
                        value.comp_positional_scarcity,
                        value.comp_fragility,
                        value.comp_ceiling,
                        value.comp_floor,
                        value.comp_rerollability,
                        value.comp_contract,
                        value.lens_production,
                        value.lens_market,
                        value.lens_insulation,
                        value.lens_team_fit,
                        value.lens_direction,
                    ],
                )


__all__ = ["IntelligenceService"]
