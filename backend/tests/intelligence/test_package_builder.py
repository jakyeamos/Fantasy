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


def test_package_builder_names_roster_aware_counter_assets(trade_seed_data):
    request = TradeRequest(
        league_id="league_x",
        user_roster_id=1,
        counterparty_roster_id=2,
        user_sends=[TradeAsset(asset_type="player", player_id="wr1")],
        user_receives=[
            TradeAsset(asset_type="player", player_id="wr2"),
            TradeAsset(
                asset_type="pick",
                pick_owner_roster_id=2,
                pick_year=2027,
                pick_round=1,
                projected_slot="1.mid",
            ),
        ],
    )
    evaluation = TradeEngine(trade_seed_data).evaluate(request)

    result = PackageBuilder(trade_seed_data).build(request, evaluation)

    assert result is not None
    assert result.roster_fit_counter is not None
    assert all(asset.label for asset in result.aggressive_open.receive_assets)
    assert all(asset.label for asset in result.roster_fit_counter.receive_assets)
    assert "lineup" in result.roster_fit_counter.reasoning.lower()
    assert any(
        asset.asset_type == "pick" and asset.pick_year == 2027
        for asset in result.roster_fit_counter.receive_assets
    )


def test_multi_team_trade_builds_primary_package(trade_seed_data):
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
    assert result is not None
    assert "participant-specific package framing" in result.aggressive_open.reasoning
    assert "scored sidecar legs" in result.fair_close.reasoning


def test_multi_team_trade_builds_package_offers_for_all_participants(trade_seed_data):
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

    assert result is not None
    assert result.participant_offers is not None
    participant_ids = {offer.roster_id for offer in result.participant_offers}
    assert participant_ids == {1, 2, 3}
    third_party_offer = next(
        offer for offer in result.participant_offers if offer.roster_id == 3
    )
    assert third_party_offer.market_fairness is not None
    assert "sidecar market score" in third_party_offer.reasoning
