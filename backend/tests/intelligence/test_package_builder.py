from fantasy.trade.models import ThirdPartyTrade, TradeAsset, TradeRequest
from fantasy.trade.package_builder import PackageBuilder
from fantasy.trade.trade_engine import TradeEngine


def _request() -> TradeRequest:
    return TradeRequest(
        league_id="league_x",
        user_roster_id=1,
        counterparty_roster_id=2,
        user_sends=[
            TradeAsset(asset_type="player", player_id="wr1"),
            TradeAsset(asset_type="pick", pick_owner_roster_id=1, pick_year=2026, pick_round=2),
        ],
        user_receives=[TradeAsset(asset_type="player", player_id="qb2")],
    )


def test_build_package(trade_seed_data):
    request = _request()
    evaluation = TradeEngine(trade_seed_data).evaluate(request)
    result = PackageBuilder(trade_seed_data).build(request, evaluation)
    assert result.aggressive_open.label == "Aggressive Open"
    assert result.fair_close.label == "Fair Close"


def test_package_builder_personalizes_when_profile_exists(trade_seed_data):
    request = _request()
    evaluation = TradeEngine(trade_seed_data).evaluate(request)
    result = PackageBuilder(trade_seed_data).build(request, evaluation)
    assert result.aggressive_open.reasoning
    assert result.fair_close.reasoning


def test_multi_team_trade_disables_package_builder(trade_seed_data):
    request = _request()
    request.third_party_trades = [
        ThirdPartyTrade(
            roster_id=3,
            sends=[TradeAsset(asset_type="player", player_id="vet1")],
            receives=[TradeAsset(asset_type="pick", pick_year=2026, pick_round=2)],
        )
    ]
    evaluation = TradeEngine(trade_seed_data).evaluate(request)
    result = PackageBuilder(trade_seed_data).build(request, evaluation)
    assert result is None
