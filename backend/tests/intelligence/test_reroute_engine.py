from fantasy.trade.models import ThirdPartyTrade, TradeAsset, TradeRequest
from fantasy.trade.reroute_engine import RerouteEngine
from fantasy.trade.trade_engine import TradeEngine


def _request() -> TradeRequest:
    return TradeRequest(
        league_id="league_x",
        user_roster_id=1,
        counterparty_roster_id=2,
        user_sends=[TradeAsset(asset_type="player", player_id="wr1")],
        user_receives=[TradeAsset(asset_type="player", player_id="wr2")],
    )


def test_generate_better_target(trade_seed_data):
    request = _request()
    evaluation = TradeEngine(trade_seed_data).evaluate(request)
    reroutes = RerouteEngine(trade_seed_data).generate(request, evaluation)
    assert any(reroute.reroute_type == "better_target" for reroute in reroutes)


def test_generate_better_package(trade_seed_data):
    request = _request()
    evaluation = TradeEngine(trade_seed_data).evaluate(request)
    reroutes = RerouteEngine(trade_seed_data).generate(request, evaluation)
    assert any(reroute.reroute_type == "better_package" for reroute in reroutes)


def test_max_reroutes_cap(trade_seed_data):
    request = _request()
    evaluation = TradeEngine(trade_seed_data).evaluate(request)
    reroutes = RerouteEngine(trade_seed_data).generate(request, evaluation)
    assert len(reroutes) <= 3


def test_reroute_has_reasoning(trade_seed_data):
    request = _request()
    evaluation = TradeEngine(trade_seed_data).evaluate(request)
    reroutes = RerouteEngine(trade_seed_data).generate(request, evaluation)
    assert reroutes
    assert all(reroute.reasoning for reroute in reroutes)


def test_multi_team_trade_keeps_primary_reroutes(trade_seed_data):
    request = _request()
    request.third_party_trades = [
        ThirdPartyTrade(
            roster_id=3,
            sends=[TradeAsset(asset_type="player", player_id="vet1")],
            receives=[TradeAsset(asset_type="pick", pick_year=2026, pick_round=2)],
        )
    ]
    evaluation = TradeEngine(trade_seed_data).evaluate(request)
    reroutes = RerouteEngine(trade_seed_data).generate(request, evaluation)
    assert reroutes
    assert any(reroute.reroute_type == "better_target" for reroute in reroutes)
