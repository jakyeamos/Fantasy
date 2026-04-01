from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


RecommendationTypeLabel = Literal[
    "trade",
    "start",
    "drop",
    "hold",
    "shop",
    "package",
    "taxi",
    "reroll",
    "bid",
    "stash",
    "direction",
]

GapClassification = Literal[
    "buy_low",
    "sell_high",
    "hold_despite_weak_market",
    "ignore_false_discount",
    "market_right_model_cautious",
    "league_specific_opportunity",
]

HorizonLabel = Literal["immediate", "this_week", "30_days", "offseason", "next_season"]
ConfidenceLabel = Literal["HIGH", "MEDIUM", "LOW"]
SupportingFactorDirection = Literal["positive", "negative", "neutral"]
SupportingFactorMagnitude = Literal["high", "medium", "low"]
TargetEntityType = Literal["player", "pick", "position", "manager"]
GapDirection = Literal["model_above", "model_below", "aligned"]


class SupportingFactor(BaseModel):
    model_config = ConfigDict(frozen=False)

    factor_name: str
    direction: SupportingFactorDirection
    magnitude: SupportingFactorMagnitude
    explanation: str


class ModelVsMarketGap(BaseModel):
    model_config = ConfigDict(frozen=False)

    market_rank: int | None = None
    model_rank: int | None = None
    market_value: float | None = None
    model_value: float | None = None
    gap_magnitude: float | None = None
    gap_direction: GapDirection | None = None
    gap_classification: GapClassification | None = None
    explanation: str | None = None


class RecommendationCard(BaseModel):
    model_config = ConfigDict(frozen=False)

    recommendation_type: RecommendationTypeLabel
    priority_rank: int
    headline: str
    action: str
    target_entity_type: TargetEntityType
    target_entity_ids: list[str]
    why_summary: str
    supporting_factors: list[SupportingFactor]
    confidence_label: ConfidenceLabel
    confidence_score: float
    downside_of_inaction: str
    what_would_change_this_call: str
    horizon: HorizonLabel
    league_specificity_notes: str | None = None
    manager_specificity_notes: str | None = None
    model_vs_market_gap: ModelVsMarketGap | None = None
    cta_label: str
    cta_destination: str


__all__ = [
    "ConfidenceLabel",
    "GapClassification",
    "HorizonLabel",
    "ModelVsMarketGap",
    "RecommendationCard",
    "RecommendationTypeLabel",
    "SupportingFactor",
]
