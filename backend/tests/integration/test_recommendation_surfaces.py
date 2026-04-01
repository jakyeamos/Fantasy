from __future__ import annotations

from fantasy.lineup.models import HygieneSuggestion
from fantasy.recommendation.card_engine import RecommendationCardEngine
from fantasy.recommendation.gap_engine import MarketGapEngine
from fantasy.recommendation.models import RecommendationCard
from fantasy.trade.models import DimensionScore, StrategicDistinction, TradeEvaluation


def test_trade_evaluation_has_recommendation_cards(db) -> None:
    engine = RecommendationCardEngine(db)
    evaluation = TradeEvaluation(
        market_fairness=DimensionScore(score=70.0, confidence="HIGH", reasoning="Value is favorable."),
        roster_fit=DimensionScore(score=64.0, confidence="MEDIUM", reasoning="Fit is solid."),
        direction_fit=DimensionScore(score=72.0, confidence="HIGH", reasoning="Advances the plan."),
        timing_quality=DimensionScore(score=61.0, confidence="MEDIUM", reasoning="Timing is live."),
        insulation_delta=DimensionScore(score=55.0, confidence="MEDIUM", reasoning="Insulation is stable."),
        liquidity_delta=DimensionScore(score=58.0, confidence="MEDIUM", reasoning="Liquidity is acceptable."),
        manager_exploit_quality=DimensionScore(score=60.0, confidence="MEDIUM", reasoning="Counterparty tendencies are targetable."),
        strategic_distinction=StrategicDistinction(
            verdict="advancing",
            headline="Market fair and advances your contender path",
            explanation="The structure helps the current direction.",
        ),
    )
    cards = engine.build_trade_card(evaluation, "league123", 1)
    assert cards
    assert cards[0].recommendation_type == "trade"


def test_hygiene_result_has_recommendation_cards(db) -> None:
    engine = RecommendationCardEngine(db)
    suggestion = HygieneSuggestion(
        action_type="consolidate",
        primary_player_ids=["p1"],
        primary_player_names=["Player One"],
        target_player_id=None,
        target_player_name=None,
        counterparty_roster_id=2,
        counterparty_name="Manager Two",
        reasoning="Bench value is better used in a package.",
        direction_fit_score=0.74,
        timing_rationale="This is the best window to combine spare assets.",
        packaging_rationale="The player is strongest as a sweetener.",
        player_context_flags=["depth_chart_competition"],
    )
    card = engine.build_hygiene_card(suggestion, "league123")
    assert card.cta_label == "Review Roster"
    assert card.recommendation_type == "trade"


def test_hold_despite_weak_market() -> None:
    assert MarketGapEngine().classify(gap=-0.25, anti_overreaction_fired=True) == "hold_despite_weak_market"


def test_recommendation_card_low_confidence_not_suppressed() -> None:
    card = RecommendationCard(
        recommendation_type="hold",
        priority_rank=44,
        headline="Hold for now",
        action="Keep the asset unless the market materially improves.",
        target_entity_type="player",
        target_entity_ids=["p2"],
        why_summary="There is still a path to recovery even with some uncertainty.",
        supporting_factors=[],
        confidence_label="LOW",
        confidence_score=0.32,
        downside_of_inaction="Selling too early can lock in the dip.",
        what_would_change_this_call="A second role loss signal.",
        horizon="30_days",
        league_specificity_notes=None,
        manager_specificity_notes=None,
        model_vs_market_gap=None,
        cta_label="Review",
        cta_destination="/league/league123",
    )
    assert card.confidence_label == "LOW"
