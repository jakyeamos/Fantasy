from __future__ import annotations

import json
from typing import Any

import duckdb

from fantasy.intelligence.constants import POSITIONAL_CLIFF_AGE, POSITIONAL_PEAK_AGE, ROUND_WEIGHTS
from fantasy.intelligence.models import ScorecardInputs, TeamScorecard


def normalize_within_league(values: dict[int, float]) -> dict[int, float]:
    if not values:
        return {}
    min_val = min(values.values())
    max_val = max(values.values())
    span = max_val - min_val
    if span < 1e-9:
        return {roster_id: 0.5 for roster_id in values}
    return {roster_id: (value - min_val) / span for roster_id, value in values.items()}


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


class ScorecardEngine:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn

    def compute(self, league_id: str, roster_id: int) -> TeamScorecard:
        return self.compute_all(league_id)[roster_id]

    def compute_all(self, league_id: str) -> dict[int, TeamScorecard]:
        roster_rows = self._conn.execute(
            "SELECT roster_id FROM rosters WHERE league_id = ? ORDER BY roster_id",
            [league_id],
        ).fetchall()
        roster_ids = [int(row[0]) for row in roster_rows]
        inputs_map = {
            roster_id: self._apply_corrections(
                self._gather_inputs(league_id, roster_id), league_id, roster_id
            )
            for roster_id in roster_ids
        }

        raw_scores: dict[str, dict[int, float]] = {
            "win_now": {},
            "future_value": {},
            "depth": {},
            "pick_capital": {},
            "flexibility": {},
            "fragility": {},
            "age_risk": {},
            "liquidity": {},
            "positional_insulation": {},
        }

        for roster_id, inputs in inputs_map.items():
            raw_scores["win_now"][roster_id] = self._score_win_now(inputs, inputs_map)
            raw_scores["future_value"][roster_id] = self._score_future_value(inputs, inputs_map)
            raw_scores["depth"][roster_id] = self._score_depth(inputs, inputs_map)
            raw_scores["pick_capital"][roster_id] = self._score_pick_capital(inputs, inputs_map)
            raw_scores["flexibility"][roster_id] = self._score_flexibility(inputs, inputs_map)
            raw_scores["fragility"][roster_id] = self._score_fragility(inputs, inputs_map)
            raw_scores["age_risk"][roster_id] = self._score_age_risk(inputs, inputs_map)
            raw_scores["liquidity"][roster_id] = self._score_liquidity(inputs, inputs_map)
            raw_scores["positional_insulation"][roster_id] = self._score_positional_insulation(
                inputs, inputs_map
            )

        normalized = {
            score_name: normalize_within_league(values)
            for score_name, values in raw_scores.items()
        }

        results: dict[int, TeamScorecard] = {}
        for roster_id in roster_ids:
            score_dict = {name: normalized[name][roster_id] for name in raw_scores}
            composite = sum(score_dict.values()) / len(score_dict)
            results[roster_id] = TeamScorecard(
                league_id=league_id,
                roster_id=roster_id,
                **score_dict,
                composite=round(composite, 3),
                computation_json=json.dumps(
                    {"raw": {name: raw_scores[name][roster_id] for name in raw_scores}},
                    separators=(",", ":"),
                ),
            )
        return results

    def _gather_inputs(self, league_id: str, roster_id: int) -> ScorecardInputs:
        league_row = self._conn.execute(
            """
            SELECT season, roster_positions, settings_blob
            FROM leagues
            WHERE league_id = ?
            LIMIT 1
            """,
            [league_id],
        ).fetchone()
        if league_row is None:
            raise ValueError(f"league not found: {league_id}")

        roster_row = self._conn.execute(
            """
            SELECT players, starters, reserve, taxi
            FROM rosters
            WHERE league_id = ? AND roster_id = ?
            LIMIT 1
            """,
            [league_id, roster_id],
        ).fetchone()
        if roster_row is None:
            raise ValueError(f"roster not found: {league_id}/{roster_id}")

        season = int(league_row[0])
        all_players = json.loads(roster_row[0] or "[]")
        starters = json.loads(roster_row[1] or "[]")
        ir = json.loads(roster_row[2] or "[]")
        taxi = json.loads(roster_row[3] or "[]")
        excluded = set(starters) | set(ir) | set(taxi)
        bench = [player_id for player_id in all_players if player_id not in excluded]

        player_rows = self._conn.execute(
            """
            SELECT player_id, COALESCE(age, 24), COALESCE(position, 'UNKNOWN')
            FROM players
            WHERE player_id IN (
                SELECT UNNEST(?)
            )
            """,
            [all_players],
        ).fetchall()
        player_ages = {str(row[0]): int(row[1]) for row in player_rows}
        player_positions = {str(row[0]): str(row[2]) for row in player_rows}

        stats_rows = self._conn.execute(
            """
            SELECT player_id, AVG(fantasy_points) AS avg_points, COUNT(*) AS games_played
            FROM player_stats_weekly
            WHERE player_id IN (
                SELECT UNNEST(?)
            )
            GROUP BY player_id
            """,
            [all_players],
        ).fetchall()
        weekly_fantasy_pts = {str(row[0]): float(row[1] or 0.0) for row in stats_rows}
        player_games_played = {str(row[0]): int(row[2] or 0) for row in stats_rows}

        adp_rows = self._conn.execute(
            """
            SELECT player_id, adp
            FROM player_adp_baseline
            WHERE player_id IN (
                SELECT UNNEST(?)
            )
            """,
            [all_players],
        ).fetchall()
        adp_ranks = {str(row[0]): float(row[1]) for row in adp_rows if row[1] is not None}

        position_medians = {
            str(row[0]): float(row[1] or 0.0)
            for row in self._conn.execute(
                """
                SELECT COALESCE(p.position, 'UNKNOWN'), AVG(s.fantasy_points)
                FROM player_stats_weekly s
                LEFT JOIN players p ON p.player_id = s.player_id
                GROUP BY COALESCE(p.position, 'UNKNOWN')
                """
            ).fetchall()
        }

        pick_rows = [
            (str(row[0]), int(row[1]), int(row[2]), str(row[3]))
            for row in self._conn.execute(
                """
                SELECT season, round, roster_id, owner_id
                FROM traded_picks
                WHERE league_id = ?
                """,
                [league_id],
            ).fetchall()
        ]

        return ScorecardInputs(
            league_id=league_id,
            roster_id=roster_id,
            season=season,
            roster_positions=json.loads(league_row[1] or "[]"),
            starters=starters,
            bench=bench,
            ir=ir,
            taxi=taxi,
            player_ages=player_ages,
            player_positions=player_positions,
            weekly_fantasy_pts=weekly_fantasy_pts,
            player_games_played=player_games_played,
            adp_ranks=adp_ranks,
            pick_rows=pick_rows,
            correction_overrides={},
            league_settings=json.loads(league_row[2] or "{}"),
            position_medians=position_medians,
        )

    def _apply_corrections(
        self, inputs: ScorecardInputs, league_id: str, roster_id: int
    ) -> ScorecardInputs:
        corrections = self._conn.execute(
            """
            SELECT entity_type, entity_id, field, corrected_value
            FROM corrections
            WHERE league_id = ?
              AND (
                entity_type = 'player'
                OR (entity_type = 'roster' AND entity_id = CAST(? AS VARCHAR))
              )
            """,
            [league_id, roster_id],
        ).fetchall()

        for entity_type, entity_id, field, corrected_value in corrections:
            if entity_type == "player":
                if field == "age":
                    inputs.player_ages[str(entity_id)] = int(corrected_value)
                elif field == "position":
                    inputs.player_positions[str(entity_id)] = str(corrected_value)
            elif entity_type == "roster":
                if field == "starters":
                    inputs.starters = json.loads(corrected_value or "[]")
                elif field == "bench":
                    inputs.bench = json.loads(corrected_value or "[]")
            inputs.correction_overrides[f"{entity_type}:{entity_id}:{field}"] = corrected_value
        return inputs

    def _value_proxy(self, inputs: ScorecardInputs, player_id: str) -> float:
        if player_id in inputs.weekly_fantasy_pts:
            return float(inputs.weekly_fantasy_pts[player_id])

        adp_rank = inputs.adp_ranks.get(player_id)
        if adp_rank is not None:
            return max(0.1, 25.0 - min(adp_rank, 250.0) / 10.0)

        position = inputs.player_positions.get(player_id, "UNKNOWN")
        return float(inputs.position_medians.get(position, 8.0))

    def _age_future_score(self, position: str, age: int) -> float:
        peak = POSITIONAL_PEAK_AGE.get(position, 28)
        cliff = POSITIONAL_CLIFF_AGE.get(position, peak + 3)
        if age <= peak:
            span = max(peak - 20, 1)
            return 0.6 + 0.4 * (peak - max(age, 20)) / span
        if age >= cliff:
            return 0.0
        return 1.0 - (age - peak) / max(cliff - peak, 1)

    def _age_risk_score(self, position: str, age: int) -> float:
        peak = POSITIONAL_PEAK_AGE.get(position, 28)
        cliff = POSITIONAL_CLIFF_AGE.get(position, peak + 3)
        if age <= peak:
            return 0.0
        if age >= cliff:
            return 1.0
        return (age - peak) / max(cliff - peak, 1)

    def _score_win_now(
        self, inputs: ScorecardInputs, all_inputs: dict[int, ScorecardInputs]
    ) -> float:
        starter_values = [self._value_proxy(inputs, player_id) for player_id in inputs.starters]
        return sum(starter_values) / max(len(starter_values), 1)

    def _score_future_value(
        self, inputs: ScorecardInputs, all_inputs: dict[int, ScorecardInputs]
    ) -> float:
        roster = inputs.starters + inputs.bench + inputs.ir + inputs.taxi
        values = [
            self._age_future_score(inputs.player_positions.get(player_id, "UNKNOWN"), inputs.player_ages.get(player_id, 24))
            for player_id in roster
        ]
        return sum(values) / max(len(values), 1)

    def _score_depth(
        self, inputs: ScorecardInputs, all_inputs: dict[int, ScorecardInputs]
    ) -> float:
        starter_avg = sum(self._value_proxy(inputs, pid) for pid in inputs.starters) / max(
            len(inputs.starters), 1
        )
        bench_values = [self._value_proxy(inputs, pid) for pid in inputs.bench]
        bench_avg = sum(bench_values) / max(len(bench_values), 1)
        if starter_avg <= 0:
            return 0.0
        return bench_avg / starter_avg

    def _score_pick_capital(
        self, inputs: ScorecardInputs, all_inputs: dict[int, ScorecardInputs]
    ) -> float:
        current_season = inputs.season
        owned_traded_keys = {
            (season, round_no, original_roster_id)
            for season, round_no, original_roster_id, owner_id in inputs.pick_rows
            if int(season) >= current_season and owner_id == str(inputs.roster_id)
        }
        routed_original_keys = {
            (season, round_no, original_roster_id)
            for season, round_no, original_roster_id, _owner_id in inputs.pick_rows
            if int(season) >= current_season and original_roster_id == inputs.roster_id
        }
        future_seasons = [str(current_season + offset) for offset in range(3)]
        untouched_original_keys = {
            (season, rnd, inputs.roster_id)
            for season in future_seasons
            for rnd in (1, 2, 3)
            if (season, rnd, inputs.roster_id) not in routed_original_keys
        }
        all_owned_picks = owned_traded_keys | untouched_original_keys
        return sum(
            ROUND_WEIGHTS.get(int(round_no), 0.5)
            for _season, round_no, _original_roster_id in all_owned_picks
        )

    def _score_flexibility(
        self, inputs: ScorecardInputs, all_inputs: dict[int, ScorecardInputs]
    ) -> float:
        positions = [
            inputs.player_positions.get(player_id, "UNKNOWN")
            for player_id in inputs.starters + inputs.bench
        ]
        if not positions:
            return 0.0
        counts: dict[str, int] = {}
        for position in positions:
            counts[position] = counts.get(position, 0) + 1
        unique_ratio = len(counts) / max(len(positions), 1)
        largest_share = max(counts.values()) / len(positions)
        return unique_ratio + (1 - largest_share)

    def _score_fragility(
        self, inputs: ScorecardInputs, all_inputs: dict[int, ScorecardInputs]
    ) -> float:
        total_possible_games = 17
        starter_games = [
            min(inputs.player_games_played.get(player_id, 0), total_possible_games)
            for player_id in inputs.starters
        ]
        if starter_games:
            avg_availability = sum(starter_games) / (len(starter_games) * total_possible_games)
        else:
            avg_availability = 0.0

        starter_values = [max(self._value_proxy(inputs, player_id), 0.0) for player_id in inputs.starters]
        total_points = sum(starter_values)
        if total_points <= 0:
            hhi_normalized = 1.0
        else:
            shares = [value / total_points for value in starter_values]
            hhi = sum(share * share for share in shares)
            min_hhi = 1.0 / max(len(starter_values), 1)
            hhi_normalized = (hhi - min_hhi) / max(1.0 - min_hhi, 1e-9)

        # Fragility reflects availability and concentration, not diagnosed injury risk.
        return 0.5 * (1 - avg_availability) + 0.5 * hhi_normalized

    def _score_age_risk(
        self, inputs: ScorecardInputs, all_inputs: dict[int, ScorecardInputs]
    ) -> float:
        roster = inputs.starters + inputs.bench
        risks = [
            self._age_risk_score(inputs.player_positions.get(player_id, "UNKNOWN"), inputs.player_ages.get(player_id, 24))
            for player_id in roster
        ]
        return sum(risks) / max(len(risks), 1)

    def _score_liquidity(
        self, inputs: ScorecardInputs, all_inputs: dict[int, ScorecardInputs]
    ) -> float:
        roster = inputs.starters + inputs.bench
        if not roster:
            return 0.0
        inverse_adp_scores = []
        for player_id in roster:
            adp = inputs.adp_ranks.get(player_id)
            if adp is None:
                inverse_adp_scores.append(0.3)
            else:
                inverse_adp_scores.append(max(0.0, 1.0 - min(adp, 250.0) / 250.0))

        txn_rows = self._conn.execute(
            """
            SELECT adds, drops
            FROM transactions
            WHERE league_id = ?
            """,
            [inputs.league_id],
        ).fetchall()
        trade_counts = {player_id: 0 for player_id in roster}
        for adds, drops in txn_rows:
            for payload in (adds, drops):
                if not payload:
                    continue
                try:
                    data = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                for player_id in data:
                    if player_id in trade_counts:
                        trade_counts[player_id] += 1

        trade_bonus = sum(min(count, 3) / 3 for count in trade_counts.values()) / max(len(roster), 1)
        return (sum(inverse_adp_scores) / len(inverse_adp_scores)) + 0.25 * trade_bonus

    def _score_positional_insulation(
        self, inputs: ScorecardInputs, all_inputs: dict[int, ScorecardInputs]
    ) -> float:
        required_slots = [
            slot
            for slot in inputs.roster_positions
            if slot not in {"BN", "IR", "TAXI", "FLEX", "SUPER_FLEX"}
        ]
        if not required_slots:
            return 0.0

        required_counts: dict[str, int] = {}
        for slot in required_slots:
            required_counts[slot] = required_counts.get(slot, 0) + 1

        bench_counts: dict[str, int] = {}
        for player_id in inputs.bench:
            position = inputs.player_positions.get(player_id, "UNKNOWN")
            bench_counts[position] = bench_counts.get(position, 0) + 1

        filled = sum(
            min(required_count, bench_counts.get(position, 0))
            for position, required_count in required_counts.items()
        )
        return filled / len(required_slots)
