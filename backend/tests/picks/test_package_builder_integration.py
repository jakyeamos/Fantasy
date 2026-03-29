from __future__ import annotations

from fantasy.rookie_pick.models import RookiePickProfile
from fantasy.rookie_pick.rookie_pick_repo import RookiePickRepo
from fantasy.trade.models import (
    DimensionScore,
    StrategicDistinction,
    TradeAsset,
    TradeEvaluation,
    TradeRequest,
)
from fantasy.trade.package_builder import PackageBuilder


def _dimension() -> DimensionScore:
    return DimensionScore(score=50.0, confidence="MEDIUM", reasoning="seed")


def _evaluation() -> TradeEvaluation:
    return TradeEvaluation(
        market_fairness=_dimension(),
        roster_fit=_dimension(),
        direction_fit=_dimension(),
        timing_quality=_dimension(),
        insulation_delta=_dimension(),
        liquidity_delta=_dimension(),
        manager_exploit_quality=_dimension(),
        strategic_distinction=StrategicDistinction(
            verdict="neutral",
            headline="seed",
            explanation="seed",
        ),
    )


def _request() -> TradeRequest:
    return TradeRequest(
        league_id="league_x",
        user_roster_id=1,
        counterparty_roster_id=2,
        user_sends=[TradeAsset(asset_type="player", player_id="send_1")],
        user_receives=[TradeAsset(asset_type="player", player_id="recv_1")],
    )


def test_package_builder_adds_pick_reasoning_when_premium_sufficient(db) -> None:
    RookiePickRepo(db).upsert_profile(
        RookiePickProfile(
            league_id="league_x",
            roster_id=2,
            computed_at="2026-01-01T00:00:00+00:00",
            pick_premium_score=0.2,
            pick_trade_evidence=3,
            draft_selection_count=2,
            show_draft_picks_tab=True,
        )
    )

    package = PackageBuilder(db).build(_request(), _evaluation())

    assert package is not None
    assert "premium for draft capital" in package.aggressive_open.reasoning


def test_package_builder_silent_omit_when_score_none(db) -> None:
    RookiePickRepo(db).upsert_profile(
        RookiePickProfile(
            league_id="league_x",
            roster_id=2,
            computed_at="2026-01-01T00:00:00+00:00",
            pick_premium_score=None,
            pick_trade_evidence=1,
            draft_selection_count=0,
        )
    )

    package = PackageBuilder(db).build(_request(), _evaluation())

    assert package is not None
    assert "premium for draft capital" not in package.aggressive_open.reasoning


def test_package_builder_silent_omit_when_evidence_thin(db) -> None:
    RookiePickRepo(db).upsert_profile(
        RookiePickProfile(
            league_id="league_x",
            roster_id=2,
            computed_at="2026-01-01T00:00:00+00:00",
            pick_premium_score=0.2,
            pick_trade_evidence=1,
            draft_selection_count=1,
            show_draft_picks_tab=False,
        )
    )

    package = PackageBuilder(db).build(_request(), _evaluation())

    assert package is not None
    assert "premium for draft capital" not in package.aggressive_open.reasoning
