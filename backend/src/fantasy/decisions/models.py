from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DecisionLane = Literal[
    "lineup",
    "waiver",
    "trade",
    "market",
    "draft",
    "portfolio",
    "manager",
]
DecisionUrgency = Literal["today", "this_week", "watch", "low"]
DecisionConfidence = Literal["high", "medium", "low"]
FreshnessState = Literal["fresh", "stale"]


class DecisionScope(BaseModel):
    model_config = ConfigDict(frozen=True)

    league_id: str | None = None
    roster_id: int | None = None
    asset_ids: list[str] = Field(default_factory=list)
    manager_id: str | None = None


class DecisionConfidenceModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    band: DecisionConfidence
    score: float | None = None
    explanation: str


class DecisionFreshness(BaseModel):
    model_config = ConfigDict(frozen=True)

    state: FreshnessState
    domains: list[str] = Field(default_factory=list)


class DecisionCta(BaseModel):
    model_config = ConfigDict(frozen=True)

    label: str
    destination: str


class DecisionCard(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    lane: DecisionLane
    scope: DecisionScope
    action: str
    outcome: str
    timing: str
    urgency: DecisionUrgency
    confidence: DecisionConfidenceModel
    acceptable_price: str | None = None
    risk: str
    invalidation: str
    evidence: list[str] = Field(default_factory=list)
    freshness: DecisionFreshness
    cta: DecisionCta


class DecisionCardsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    cards: list[DecisionCard] = Field(default_factory=list)
    total: int
    computed_at: str


__all__ = ["DecisionCard", "DecisionCardsResponse"]
