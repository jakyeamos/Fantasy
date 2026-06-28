from __future__ import annotations

from typing import get_args

import duckdb
import pytest
from pydantic import ValidationError

from fantasy.recommendation.card_engine import RecommendationCardEngine, compute_priority
from fantasy.recommendation.constants import confidence_label_from_score
from fantasy.recommendation.models import GapClassification, RecommendationCard, SupportingFactor


def _base_card() -> dict:
    return {
        "recommendation_type": "trade",
        "priority_rank": 7,
        "headline": "Trade for a stronger weekly anchor",
        "action": "Push this structure forward.",
        "target_entity_type": "player",
        "target_entity_ids": ["player-1"],
        "why_summary": "This improves weekly insulation and market leverage.",
        "supporting_factors": [
            {
                "factor_name": "Direction Fit",
                "direction": "positive",
                "magnitude": "high",
                "explanation": "The trade advances your active team direction.",
            }
        ],
        "confidence_label": "HIGH",
        "confidence_score": 0.81,
        "downside_of_inaction": "You risk missing the current price window.",
        "what_would_change_this_call": "A better counter or a material role change.",
        "horizon": "30_days",
        "league_specificity_notes": None,
        "manager_specificity_notes": None,
        "model_vs_market_gap": None,
        "cta_label": "Evaluate This Trade",
        "cta_destination": "/trades?leagueId=test",
    }


def test_card_model_has_required_fields() -> None:
    card = RecommendationCard(**_base_card())
    assert card.headline == "Trade for a stronger weekly anchor"

    payload = _base_card()
    payload.pop("headline")
    with pytest.raises(ValidationError):
        RecommendationCard(**payload)


def test_card_model_accepts_trend_result() -> None:
    payload = _base_card()
    payload["trend_result"] = {
        "player_id": "player-1",
        "trend_label": "will_rise",
        "confidence": "HIGH",
        "delta_magnitude": 0.12,
        "component_deltas": {"comp_short_term": 0.08},
        "adp_delta": 4.0,
        "seasons_compared": 2,
        "backfilled": False,
    }

    card = RecommendationCard(**payload)

    assert card.trend_result is not None
    assert card.trend_result.trend_label == "will_rise"


def test_supporting_factor_direction_values() -> None:
    factor = SupportingFactor(
        factor_name="Market signal",
        direction="positive",
        magnitude="medium",
        explanation="The market is lighter than the model.",
    )
    assert factor.direction == "positive"

    with pytest.raises(ValidationError):
        SupportingFactor(
            factor_name="Market signal",
            direction="invalid",
            magnitude="medium",
            explanation="Nope",
        )


def test_priority_rank_max() -> None:
    assert compute_priority(1.0, 1.0, 1.0, 1.0) == 1


def test_priority_rank_min() -> None:
    assert compute_priority(0.0, 0.0, 0.0, 0.0) == 100


def test_priority_rank_partial() -> None:
    result = compute_priority(0.5, 0.8, 0.6, 0.7)
    assert isinstance(result, int)
    assert 1 <= result <= 100


def test_confidence_contract_high() -> None:
    assert confidence_label_from_score(0.80) == "HIGH"


def test_confidence_contract_medium() -> None:
    assert confidence_label_from_score(0.60) == "MEDIUM"


def test_confidence_contract_low() -> None:
    assert confidence_label_from_score(0.30) == "LOW"


def test_confidence_contract_boundary_medium() -> None:
    assert confidence_label_from_score(0.75) == "HIGH"


def test_gap_classification_literals() -> None:
    assert set(get_args(GapClassification)) == {
        "buy_low",
        "sell_high",
        "hold_despite_weak_market",
        "ignore_false_discount",
        "market_right_model_cautious",
        "league_specific_opportunity",
    }


def test_recommendation_card_engine_initializes() -> None:
    conn = duckdb.connect(":memory:")
    try:
        engine = RecommendationCardEngine(conn)
        assert isinstance(engine, RecommendationCardEngine)
    finally:
        conn.close()
