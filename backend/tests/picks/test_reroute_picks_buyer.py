from __future__ import annotations

from fantasy.rookie_pick.models import RookiePickProfile
from fantasy.rookie_pick.rookie_pick_repo import RookiePickRepo
from fantasy.trade.models import RerouteResult, TradeAsset
from fantasy.trade.reroute_engine import RerouteEngine


def test_picks_buyer_reroute_fires_when_above_threshold(db) -> None:
    RookiePickRepo(db).upsert_profile(
        RookiePickProfile(
            league_id="league_x",
            roster_id=2,
            computed_at="2026-01-01T00:00:00+00:00",
            pick_premium_score=0.2,
            pick_trade_evidence=3,
        )
    )

    reroute = RerouteEngine(db)._generate_picks_buyer_reroute(
        "league_x",
        2,
        [TradeAsset(asset_type="player", player_id="recv_1")],
    )

    assert reroute is not None
    assert reroute.reroute_type == "picks_buyer"


def test_picks_buyer_reroute_silent_omit_when_score_none(db) -> None:
    RookiePickRepo(db).upsert_profile(
        RookiePickProfile(
            league_id="league_x",
            roster_id=2,
            computed_at="2026-01-01T00:00:00+00:00",
            pick_premium_score=None,
            pick_trade_evidence=1,
        )
    )

    reroute = RerouteEngine(db)._generate_picks_buyer_reroute(
        "league_x",
        2,
        [TradeAsset(asset_type="player", player_id="recv_1")],
    )

    assert reroute is None


def test_picks_buyer_reroute_not_fired_when_user_receives_picks(db) -> None:
    RookiePickRepo(db).upsert_profile(
        RookiePickProfile(
            league_id="league_x",
            roster_id=2,
            computed_at="2026-01-01T00:00:00+00:00",
            pick_premium_score=0.2,
            pick_trade_evidence=3,
        )
    )

    reroute = RerouteEngine(db)._generate_picks_buyer_reroute(
        "league_x",
        2,
        [TradeAsset(asset_type="pick", pick_owner_roster_id=2, pick_year=2026, pick_round=1)],
    )

    assert reroute is None


def test_reroute_result_literal_includes_picks_buyer() -> None:
    result = RerouteResult(
        reroute_type="picks_buyer",
        headline="seed",
        reasoning="seed",
    )
    assert result.reroute_type == "picks_buyer"
