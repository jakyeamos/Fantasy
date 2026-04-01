from __future__ import annotations

from fantasy.market.market_service import MarketService
from fantasy.recommendation.gap_engine import MarketGapEngine
from fantasy.recommendation.models import ModelVsMarketGap


def test_gap_buy_low() -> None:
    assert MarketGapEngine().classify(0.25, False) == "buy_low"


def test_gap_sell_high() -> None:
    assert MarketGapEngine().classify(-0.25, False) == "sell_high"


def test_gap_hold_despite_weak_market() -> None:
    assert MarketGapEngine().classify(0.0, True) == "hold_despite_weak_market"


def test_gap_aligned() -> None:
    assert MarketGapEngine().classify(0.05, False) == "market_right_model_cautious"


def test_gap_league_specific() -> None:
    assert MarketGapEngine().classify(0.15, False) == "league_specific_opportunity"


def test_gap_ignore_false_discount() -> None:
    assert MarketGapEngine().classify(-0.15, False) == "ignore_false_discount"


def test_compute_model_vs_market_gap_returns_correct_type() -> None:
    gap = MarketGapEngine().compute_model_vs_market_gap(
        lens_production=0.76,
        lens_market=0.51,
        fantasycalc_rank=12,
        player_total_count=300,
        anti_overreaction_fired=False,
    )
    assert isinstance(gap, ModelVsMarketGap)
    assert gap.gap_classification == "buy_low"


def test_hold_despite_weak_market_is_first_class() -> None:
    assert MarketGapEngine().classify(-0.25, True) == "hold_despite_weak_market"


def test_lens_market_neutral_fallback(db) -> None:
    db.execute(
        """
        INSERT INTO leagues (league_id, name, season, scoring_settings, roster_positions, ppr, superflex, tep)
        VALUES ('league_x', 'League X', '2025', '{}', '[]', 1.0, FALSE, FALSE)
        """
    )
    assert MarketService(db).get_lens_market_value("missing-player", "league_x") == 0.5
