from fantasy.trade.models import DimensionScore, ThirdPartyTrade, TradeAsset, TradeRequest
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


def test_multi_team_context_reduces_dimension_confidence(trade_seed_data):
    engine = TradeEngine(trade_seed_data)
    request = _request()
    request.third_party_trades = [
        ThirdPartyTrade(
            roster_id=3,
            sends=[TradeAsset(asset_type="player", player_id="vet1")],
            receives=[TradeAsset(asset_type="pick", pick_year=2026, pick_round=2)],
        )
    ]
    evaluation = engine.evaluate(request)
    assert evaluation.market_fairness.confidence == "MEDIUM"
    assert "Multi-team context:" in evaluation.market_fairness.reasoning
    assert evaluation.third_party_evaluations is not None
    assert evaluation.third_party_evaluations[0].roster_id == 3
    assert 0.0 <= evaluation.third_party_evaluations[0].market_fairness.score <= 100.0
    assert "scored third-party leg" in evaluation.strategic_distinction.explanation


def test_rebuild_pick_proxy_supports_current_labels(trade_seed_data):
    engine = TradeEngine(trade_seed_data)
    pick_asset = TradeAsset(asset_type="pick", pick_year=2026, pick_round=1)
    one_year_punt = engine._build_pick_proxy(pick_asset, "one_year_punt")
    retool = engine._build_pick_proxy(pick_asset, "retool")
    assert one_year_punt["lens_direction"] > retool["lens_direction"]
