import math
import json

import pytest

from fantasy.corrections.override_service import CorrectionCreate, OverrideService
from fantasy.intelligence.scorecard_engine import ScorecardEngine


def test_all_subscores_present(phase2_seed_data):
    scorecards = ScorecardEngine(phase2_seed_data).compute_all("league_x")
    scorecard = scorecards[1]
    for field in [
        "win_now",
        "future_value",
        "depth",
        "pick_capital",
        "flexibility",
        "fragility",
        "age_risk",
        "liquidity",
        "positional_insulation",
    ]:
        assert getattr(scorecard, field) is not None


def test_subscores_in_range(phase2_seed_data):
    scorecards = ScorecardEngine(phase2_seed_data).compute_all("league_x")
    for scorecard in scorecards.values():
        for value in scorecard.as_dict().values():
            assert 0.0 <= value <= 1.0


def test_pick_capital_dual_source(phase2_seed_data):
    scorecards = ScorecardEngine(phase2_seed_data).compute_all("league_x")
    assert scorecards[1].pick_capital > scorecards[2].pick_capital


def test_pick_capital_is_slot_sensitive_for_current_firsts(phase2_seed_data):
    phase2_seed_data.execute("DELETE FROM traded_picks WHERE league_id = 'league_x'")
    phase2_seed_data.execute(
        """
        INSERT INTO standings (id, league_id, roster_id, wins, losses, ties, fpts, fpts_against)
        VALUES
            (1, 'league_x', 1, 0, 14, 0, 100.0, 180.0),
            (2, 'league_x', 2, 14, 0, 0, 180.0, 100.0)
        """
    )
    phase2_seed_data.execute(
        """
        INSERT INTO league_draft_order_rules (
            id, league_id, non_playoff_basis, playoff_ordering, tiebreaker
        )
        VALUES (1, 'league_x', 'inverse_standings', 'by_finish', 'points_against')
        """
    )

    scorecards = ScorecardEngine(phase2_seed_data).compute_all("league_x")

    assert scorecards[1].pick_capital > scorecards[2].pick_capital


def test_missing_stats_defaults(phase2_seed_data):
    phase2_seed_data.execute(
        """
        INSERT INTO rosters (id, league_id, roster_id, owner_id, starters, players, reserve, taxi)
        VALUES (3, 'league_x', 3, 'user_c', '["rookie1"]', '["rookie1"]', '[]', '[]')
        """
    )
    scorecards = ScorecardEngine(phase2_seed_data).compute_all("league_x")
    assert isinstance(scorecards[3].win_now, float)
    assert not math.isnan(scorecards[3].win_now)


def test_corrections_applied_before_scoring(phase2_seed_data):
    engine = ScorecardEngine(phase2_seed_data)
    baseline = engine.compute_all("league_x")[1].age_risk
    service = OverrideService()
    for player_id in ("qb1", "rb1", "wr1", "te1"):
        service.create_correction(
            phase2_seed_data,
            CorrectionCreate(
                league_id="league_x",
                entity_type="player",
                entity_id=player_id,
                field="age",
                original_value="24",
                corrected_value="36",
            ),
        )
    updated = engine.compute_all("league_x")[1].age_risk
    assert updated > baseline


def test_future_value_downweights_unproven_young_players(phase2_seed_data):
    phase2_seed_data.execute(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES
            ('uqb1','Unknown QB','QB','U',21,'{}'),
            ('urb1','Unknown RB','RB','U',21,'{}'),
            ('uwr1','Unknown WR 1','WR','U',21,'{}'),
            ('ute1','Unknown TE','TE','U',21,'{}'),
            ('uwr2','Unknown WR 2','WR','U',21,'{}'),
            ('urb2','Unknown RB 2','RB','U',21,'{}')
        """
    )
    phase2_seed_data.execute(
        """
        INSERT INTO rosters (id, league_id, roster_id, owner_id, starters, players, reserve, taxi)
        VALUES (
            3,
            'league_x',
            3,
            'user_c',
            '["uqb1","urb1","uwr1","ute1"]',
            '["uqb1","urb1","uwr1","ute1","uwr2","urb2"]',
            '[]',
            '[]'
        )
        """
    )

    scorecards = ScorecardEngine(phase2_seed_data).compute_all("league_x")

    assert scorecards[3].future_value < scorecards[1].future_value


def test_future_value_includes_pick_capital(phase2_seed_data):
    phase2_seed_data.execute(
        """
        INSERT INTO rosters (id, league_id, roster_id, owner_id, starters, players, reserve, taxi)
        VALUES (
            3,
            'league_x',
            3,
            'user_c',
            '["qb2","rb2","wr2","te2"]',
            '["qb2","rb2","wr2","te2","rbb2","wrb2"]',
            '[]',
            '[]'
        )
        """
    )
    phase2_seed_data.execute(
        """
        INSERT INTO traded_picks (id, league_id, season, round, roster_id, owner_id, previous_owner_id)
        VALUES
            (3, 'league_x', '2025', 1, 1, '3', '1'),
            (4, 'league_x', '2025', 2, 1, '3', '1'),
            (5, 'league_x', '2026', 1, 2, '3', '2')
        """
    )

    scorecards = ScorecardEngine(phase2_seed_data).compute_all("league_x")

    assert scorecards[3].future_value > scorecards[2].future_value


def test_league_relative_normalization(phase2_seed_data):
    scorecards = ScorecardEngine(phase2_seed_data).compute_all("league_x")
    assert scorecards[1].pick_capital > scorecards[2].pick_capital
    assert 0.0 <= scorecards[1].pick_capital <= 1.0
    assert 0.0 <= scorecards[2].pick_capital <= 1.0


def test_scorecard_semantics_are_self_describing(phase2_seed_data):
    scorecard = ScorecardEngine(phase2_seed_data).compute_all("league_x")[1]
    metadata = json.loads(scorecard.computation_json)

    assert metadata["schema_version"] == "team-scorecard-semantics/1.0"
    assert metadata["model_version"] == "team-scorecard/2.0"
    assert metadata["stats_season"] == 2024
    assert metadata["composite_label"] == "beneficial_team_quality"
    assert metadata["dimensions"]["fragility"]["direction"] == "lower_is_better"
    assert metadata["dimensions"]["win_now"]["direction"] == "higher_is_better"
    assert "raw" in metadata["dimensions"]["win_now"]
    assert "percentile" in metadata["dimensions"]["win_now"]
    beneficial = [
        dimension["beneficial_score"]
        for dimension in metadata["dimensions"].values()
    ]
    assert scorecard.composite == pytest.approx(sum(beneficial) / len(beneficial), abs=1e-3)


def test_cross_season_clone_is_not_double_counted(phase2_seed_data):
    rows = phase2_seed_data.execute(
        "SELECT * EXCLUDE (season) FROM player_stats_weekly WHERE season = 2024"
    ).fetchall()
    columns = [
        row[0]
        for row in phase2_seed_data.execute(
            "DESCRIBE player_stats_weekly"
        ).fetchall()
        if row[0] != "season"
    ]
    # Expand past the clone detector's minimum while preserving the actual roster rows.
    for suffix in range(1, 10):
        for row in rows:
            values = list(row)
            values[0] = f"{values[0]}-{suffix}"
            phase2_seed_data.execute(
                f"INSERT INTO player_stats_weekly ({','.join(columns)}, season) VALUES ({','.join(['?'] * len(columns))}, 2024)",
                values,
            )
    phase2_seed_data.execute(
        "INSERT INTO player_stats_weekly SELECT * REPLACE (2025 AS season) FROM player_stats_weekly WHERE season = 2024"
    )

    inputs = ScorecardEngine(phase2_seed_data)._gather_inputs("league_x", 1)

    assert inputs.stats_season == 2024
    assert inputs.player_games_played["wr1"] == 1


def test_fragility_availability_proxy(phase2_seed_data):
    phase2_seed_data.execute(
        "DELETE FROM player_stats_weekly WHERE player_id IN ('qb1', 'rb1', 'wr1', 'te1')"
    )
    scorecards = ScorecardEngine(phase2_seed_data).compute_all("league_x")
    assert scorecards[1].fragility > scorecards[2].fragility


def test_positional_insulation_requires_distinct_bench_cover(phase2_seed_data):
    phase2_seed_data.execute(
        """
        UPDATE leagues
        SET roster_positions = '["QB","RB","RB","WR","TE","BN"]'
        WHERE league_id = 'league_x'
        """
    )
    phase2_seed_data.execute(
        """
        UPDATE rosters
        SET starters = '["qb1","rb1","rbb1","wr1","te1"]',
            players = '["qb1","rb1","rbb1","wr1","te1","vet1"]'
        WHERE league_id = 'league_x' AND roster_id = 1
        """
    )

    engine = ScorecardEngine(phase2_seed_data)
    inputs = engine._gather_inputs("league_x", 1)
    score = engine._score_positional_insulation(inputs, {1: inputs})

    assert score == pytest.approx(0.2)
