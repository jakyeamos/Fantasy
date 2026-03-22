from fantasy.trade.models import DimensionScore, TradeAsset, TradeRequest
from fantasy.trade.trade_engine import TradeEngine


def _request() -> TradeRequest:
    return TradeRequest(
        league_id="league_x",
        user_roster_id=1,
        counterparty_roster_id=2,
        user_sends=[TradeAsset(asset_type="player", player_id="wr1")],
        user_receives=[TradeAsset(asset_type="player", player_id="qb2")],
    )


def test_evaluate_trade(trade_seed_data):
    engine = TradeEngine(trade_seed_data)
    evaluation = engine.evaluate(_request())
    assert evaluation.market_fairness.score >= 0
    assert evaluation.manager_exploit_quality.reasoning


def test_dimension_scores(trade_seed_data):
    engine = TradeEngine(trade_seed_data)
    evaluation = engine.evaluate(_request())
    dimensions = [
        evaluation.market_fairness,
        evaluation.roster_fit,
        evaluation.direction_fit,
        evaluation.timing_quality,
        evaluation.insulation_delta,
        evaluation.liquidity_delta,
        evaluation.manager_exploit_quality,
    ]
    assert len(dimensions) == 7
    for dimension in dimensions:
        assert isinstance(dimension, DimensionScore)
        assert 0.0 <= dimension.score <= 100.0
        assert dimension.confidence in {"HIGH", "MEDIUM", "LOW"}


def test_reroute_paths(trade_seed_data):
    engine = TradeEngine(trade_seed_data)
    evaluation = engine.evaluate(_request())
    assert evaluation.reroutes is None
    assert evaluation.package is None


def test_strategic_distinction_negative(trade_seed_data):
    engine = TradeEngine(trade_seed_data)
    distinction = engine._compute_strategic_distinction(
        DimensionScore(score=50, confidence="HIGH", reasoning=""),
        DimensionScore(score=40, confidence="HIGH", reasoning=""),
        "hard_rebuild",
    )
    assert distinction.verdict == "negative"


def test_strategic_distinction_advancing(trade_seed_data):
    engine = TradeEngine(trade_seed_data)
    distinction = engine._compute_strategic_distinction(
        DimensionScore(score=50, confidence="HIGH", reasoning=""),
        DimensionScore(score=60, confidence="HIGH", reasoning=""),
        "hard_rebuild",
    )
    assert distinction.verdict == "advancing"


def test_strategic_distinction_neutral(trade_seed_data):
    engine = TradeEngine(trade_seed_data)
    distinction = engine._compute_strategic_distinction(
        DimensionScore(score=50, confidence="HIGH", reasoning=""),
        DimensionScore(score=50, confidence="HIGH", reasoning=""),
        "hard_rebuild",
    )
    assert distinction.verdict == "neutral"


def test_no_manager_profile_returns_low_confidence(trade_seed_data):
    trade_seed_data.execute("DELETE FROM manager_profiles WHERE league_id = 'league_x' AND roster_id = 2")
    trade_seed_data.execute(
        "DELETE FROM manager_pitch_angles WHERE league_id = 'league_x' AND roster_id = 2"
    )
    engine = TradeEngine(trade_seed_data)
    evaluation = engine.evaluate(_request())
    assert evaluation.manager_exploit_quality.confidence == "LOW"
