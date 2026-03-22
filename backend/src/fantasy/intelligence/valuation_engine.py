from __future__ import annotations

import duckdb

from fantasy.intelligence.constants import (
    DIRECTION_VALUE_WEIGHTS,
    FORMAT_MULTIPLIERS,
    POSITIONAL_CLIFF_AGE,
    POSITIONAL_PEAK_AGE,
)
from fantasy.intelligence.models import PlayerValue


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


class ValuationEngine:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn

    def compute_player(self, league_id: str, roster_id: int, player_id: str, direction_label: str) -> PlayerValue:
        player_row = self._conn.execute(
            """
            SELECT full_name, COALESCE(position, 'UNKNOWN'), COALESCE(age, 24)
            FROM players
            WHERE player_id = ?
            LIMIT 1
            """,
            [player_id],
        ).fetchone()
        if player_row is None:
            raise ValueError(f"player not found: {player_id}")

        league_row = self._conn.execute(
            """
            SELECT ppr, superflex, tep
            FROM leagues
            WHERE league_id = ?
            LIMIT 1
            """,
            [league_id],
        ).fetchone()
        if league_row is None:
            raise ValueError(f"league not found: {league_id}")

        stats_row = self._conn.execute(
            """
            SELECT AVG(fantasy_points) AS ppg,
                   COUNT(*) AS games_played,
                   MAX(fantasy_points) AS best_week
            FROM player_stats_weekly
            WHERE player_id = ?
            """,
            [player_id],
        ).fetchone()
        adp_row = self._conn.execute(
            """
            SELECT adp
            FROM player_adp_baseline
            WHERE player_id = ?
            LIMIT 1
            """,
            [player_id],
        ).fetchone()

        position = str(player_row[1])
        age = int(player_row[2])
        ppg = float(stats_row[0]) if stats_row and stats_row[0] is not None else None
        games_played = int(stats_row[1]) if stats_row and stats_row[1] is not None else 0
        best_week = float(stats_row[2]) if stats_row and stats_row[2] is not None else None
        adp = float(adp_row[0]) if adp_row and adp_row[0] is not None else None

        current_production = self._production_score(ppg, position, league_row)
        role_stability = _clamp01(games_played / 17.0) if games_played else 0.45
        short_term = _clamp01(0.7 * current_production + 0.3 * role_stability)
        age_curve = self._age_curve_score(position, age)
        fragility = _clamp01(1.0 - role_stability)
        market_liquidity = _clamp01(1.0 - min(adp or 200.0, 250.0) / 250.0)
        positional_scarcity = self._positional_scarcity(position, league_row)
        ceiling = _clamp01(((best_week if best_week is not None else (ppg or 10.0)) / 30.0))
        floor = _clamp01(((ppg if ppg is not None else 8.0) / 20.0) * max(role_stability, 0.5))
        rerollability = self._rerollability(position, age)
        contract = _clamp01(0.6 * age_curve + 0.4 * role_stability)
        insulation = _clamp01((role_stability + age_curve + (1.0 - fragility)) / 3.0)

        player_value = PlayerValue(
            league_id=league_id,
            roster_id=roster_id,
            player_id=player_id,
            comp_current_production=current_production,
            comp_short_term=short_term,
            comp_role_stability=role_stability,
            comp_age_curve=age_curve,
            comp_insulation=insulation,
            comp_market_liquidity=market_liquidity,
            comp_positional_scarcity=positional_scarcity,
            comp_fragility=fragility,
            comp_ceiling=ceiling,
            comp_floor=floor,
            comp_rerollability=rerollability,
            comp_contract=contract,
        )
        player_value.lens_production = _clamp01(
            (current_production + short_term + ceiling + floor) / 4.0
        )
        player_value.lens_market = _clamp01(
            (market_liquidity + positional_scarcity + rerollability) / 3.0
        )
        player_value.lens_insulation = _clamp01(
            (insulation + role_stability + (1.0 - fragility) + contract) / 4.0
        )
        player_value.lens_team_fit = _clamp01((positional_scarcity + role_stability) / 2.0)
        player_value.lens_direction = self._direction_lens(player_value, direction_label)
        return player_value

    def compute_all(self, league_id: str, roster_id: int, direction_label: str) -> dict[str, PlayerValue]:
        roster_row = self._conn.execute(
            """
            SELECT players
            FROM rosters
            WHERE league_id = ? AND roster_id = ?
            LIMIT 1
            """,
            [league_id, roster_id],
        ).fetchone()
        if roster_row is None:
            return {}
        player_ids = list(dict.fromkeys(__import__("json").loads(roster_row[0] or "[]")))
        return {
            player_id: self.compute_player(league_id, roster_id, player_id, direction_label)
            for player_id in player_ids
        }

    def _production_score(self, ppg: float | None, position: str, league_row: tuple[float, bool, bool]) -> float:
        base = _clamp01((ppg if ppg is not None else 8.0) / 25.0)
        return _clamp01(base * self._format_multiplier(position, league_row))

    def _age_curve_score(self, position: str, age: int) -> float:
        peak = POSITIONAL_PEAK_AGE.get(position, 28)
        cliff = POSITIONAL_CLIFF_AGE.get(position, peak + 3)
        if age <= peak:
            return 1.0
        if age >= cliff:
            return 0.0
        return 1.0 - (age - peak) / max(cliff - peak, 1)

    def _format_multiplier(self, position: str, league_row: tuple[float, bool, bool]) -> float:
        ppr, superflex, tep = float(league_row[0]), bool(league_row[1]), bool(league_row[2])
        if ppr >= 1.0:
            ppr_key = "ppr_1.0"
        elif ppr >= 0.5:
            ppr_key = "ppr_0.5"
        else:
            ppr_key = "ppr_0.0"
        multiplier = FORMAT_MULTIPLIERS[ppr_key].get(position, 1.0)
        if superflex:
            multiplier *= FORMAT_MULTIPLIERS["superflex"].get(position, 1.0)
        if tep:
            multiplier *= FORMAT_MULTIPLIERS["tep"].get(position, 1.0)
        return multiplier

    def _positional_scarcity(self, position: str, league_row: tuple[float, bool, bool]) -> float:
        base = {"QB": 0.50, "RB": 0.72, "WR": 0.68, "TE": 0.58}.get(position, 0.4)
        return _clamp01(base * self._format_multiplier(position, league_row) / 1.35)

    def _rerollability(self, position: str, age: int) -> float:
        base = {"RB": 0.85, "WR": 0.60, "TE": 0.48, "QB": 0.35}.get(position, 0.5)
        if age > POSITIONAL_CLIFF_AGE.get(position, 31):
            base += 0.10
        return _clamp01(base)

    def _direction_lens(self, value: PlayerValue, direction_label: str) -> float:
        weights = DIRECTION_VALUE_WEIGHTS[direction_label]
        component_scores = {
            "current_production": value.comp_current_production or 0.0,
            "short_term": value.comp_short_term or 0.0,
            "role_stability": value.comp_role_stability or 0.0,
            "age_curve": value.comp_age_curve or 0.0,
            "insulation": value.comp_insulation or 0.0,
            "market_liquidity": value.comp_market_liquidity or 0.0,
            "positional_scarcity": value.comp_positional_scarcity or 0.0,
            "fragility": value.comp_fragility or 0.0,
            "ceiling": value.comp_ceiling or 0.0,
            "floor": value.comp_floor or 0.0,
            "rerollability": value.comp_rerollability or 0.0,
            "contract": value.comp_contract or 0.0,
        }
        total = 0.0
        weight_sum = 0.0
        for component, weight in weights.items():
            score = component_scores[component]
            total += (score if weight >= 0 else (1.0 - score)) * abs(weight)
            weight_sum += abs(weight)
        return _clamp01(total / max(weight_sum, 1e-9))


__all__ = ["ValuationEngine"]
