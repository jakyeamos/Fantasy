import math

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


def test_league_relative_normalization(phase2_seed_data):
    scorecards = ScorecardEngine(phase2_seed_data).compute_all("league_x")
    assert scorecards[1].pick_capital > scorecards[2].pick_capital
    assert 0.0 <= scorecards[1].pick_capital <= 1.0
    assert 0.0 <= scorecards[2].pick_capital <= 1.0


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
