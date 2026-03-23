from fantasy.intelligence.constants import DIRECTION_MOVE_MATRIX, VALID_DIRECTION_LABELS
from fantasy.intelligence.direction_engine import DirectionEngine
from fantasy.intelligence.models import TeamScorecard


def make_scorecard(**overrides) -> TeamScorecard:
    defaults = {
        "league_id": "test_league",
        "roster_id": 1,
        "win_now": 0.5,
        "future_value": 0.5,
        "depth": 0.5,
        "pick_capital": 0.5,
        "flexibility": 0.5,
        "fragility": 0.5,
        "age_risk": 0.5,
        "liquidity": 0.5,
        "positional_insulation": 0.5,
        "composite": 0.5,
    }
    defaults.update(overrides)
    return TeamScorecard(**defaults)


def test_valid_label():
    result = DirectionEngine().classify(make_scorecard())
    assert result.primary_label in VALID_DIRECTION_LABELS


def test_contender_signal():
    result = DirectionEngine().classify(
        make_scorecard(win_now=0.9, future_value=0.1, depth=0.8, fragility=0.1, age_risk=0.1)
    )
    assert result.primary_label in {"true_contender", "fragile_contender", "fringe_playoff"}


def test_rebuild_signal():
    result = DirectionEngine().classify(
        make_scorecard(win_now=0.1, future_value=0.9, pick_capital=0.9, age_risk=0.8, liquidity=0.8)
    )
    assert result.primary_label in {"hard_rebuild", "elite_value_accumulation", "one_year_punt"}


def test_confidence_range():
    engine = DirectionEngine()
    scorecards = [
        make_scorecard(win_now=0.9, future_value=0.2),
        make_scorecard(win_now=0.2, future_value=0.9),
        make_scorecard(depth=0.8, fragility=0.9),
        make_scorecard(flexibility=0.9, liquidity=0.9),
        make_scorecard(age_risk=0.9, future_value=0.2),
        make_scorecard(positional_insulation=0.8, depth=0.8),
        make_scorecard(win_now=0.4, future_value=0.6, pick_capital=0.7),
        make_scorecard(win_now=0.7, future_value=0.4, liquidity=0.6),
        make_scorecard(fragility=0.2, age_risk=0.7, pick_capital=0.8),
        make_scorecard(depth=0.4, flexibility=0.8, future_value=0.7),
    ]
    for scorecard in scorecards:
        confidence = engine.classify(scorecard).confidence
        assert 0.0 <= confidence <= 1.0


def test_minimum_alternates():
    result = DirectionEngine().classify(make_scorecard())
    assert len(result.alternates) >= 2


def test_low_confidence_reasoning():
    result = DirectionEngine().classify(make_scorecard())
    assert result.confidence < 0.40
    assert result.reasoning.startswith("Low confidence")


def test_delta_present():
    result = DirectionEngine().classify(make_scorecard(win_now=0.8, future_value=0.2))
    assert {"flip_to", "dimension", "change_needed", "direction"} <= set(result.delta)


def test_clear_contender_signal_has_high_confidence():
    result = DirectionEngine().classify(
        make_scorecard(
            win_now=0.9,
            future_value=0.2,
            depth=0.8,
            pick_capital=0.2,
            flexibility=0.4,
            fragility=0.1,
            age_risk=0.1,
            liquidity=0.2,
            positional_insulation=0.8,
        )
    )
    assert result.confidence >= 0.7
    assert not result.reasoning.startswith("Low confidence")


def test_rebuild_signal_with_close_alternates_is_medium_confidence():
    result = DirectionEngine().classify(
        make_scorecard(
            win_now=0.1,
            future_value=0.9,
            depth=0.3,
            pick_capital=0.9,
            flexibility=0.7,
            fragility=0.3,
            age_risk=0.8,
            liquidity=0.8,
            positional_insulation=0.3,
        )
    )
    assert 0.4 <= result.confidence < 0.7
    assert not result.reasoning.startswith("Low confidence")


def test_move_matrix_completeness():
    for label in VALID_DIRECTION_LABELS:
        assert DIRECTION_MOVE_MATRIX[label]["approved"]
        assert DIRECTION_MOVE_MATRIX[label]["discouraged"]


def test_ranked_moves():
    engine = DirectionEngine()
    moves = engine.rank_moves("hard_rebuild", make_scorecard(win_now=0.1, pick_capital=0.1))
    assert moves
    assert all(move in DIRECTION_MOVE_MATRIX["hard_rebuild"]["approved"] for move in moves)
