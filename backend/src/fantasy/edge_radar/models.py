from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from fantasy.context.models import EvidenceFreshness

EdgeSignalType = Literal[
    "buy_low",
    "buy_high",
    "sell_high",
    "sell_low",
    "waiver_pickup",
    "draft_diamond",
    "portfolio_hedge",
    "manager_exploit",
]
SourceStatus = Literal["ready", "missing", "degraded"]
EdgeConfidence = Literal["HIGH", "MEDIUM", "LOW"]


class SourceHealth(BaseModel):
    model_config = ConfigDict(frozen=False)

    source: str
    status: SourceStatus
    detail: str
    freshness: float


class SimilarPlayerOutcome(BaseModel):
    model_config = ConfigDict(frozen=False)

    player_id: str
    player_name: str
    similarity_score: float
    context: str
    outcome_summary: str


class EdgeRadarItem(BaseModel):
    model_config = ConfigDict(frozen=False)

    id: str
    signal_type: EdgeSignalType
    league_id: str | None = None
    roster_id: int | None = None
    player_id: str | None = None
    player_name: str
    position: str
    action_label: str
    market_delta: float
    market_price: float
    model_value: float
    conviction_score: float
    confidence: EdgeConfidence
    acceptable_price: str
    timing_window: str
    source_evidence: list[str] = Field(default_factory=list)
    evidence_freshness: EvidenceFreshness = Field(default_factory=EvidenceFreshness)
    similarity_score: float = 0.0
    similar_player_outcomes: list[SimilarPlayerOutcome] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    cta_label: str
    cta_destination: str


class EdgeRadarResponse(BaseModel):
    model_config = ConfigDict(frozen=False)

    items: list[EdgeRadarItem] = Field(default_factory=list)
    source_health: list[SourceHealth] = Field(default_factory=list)
    total: int
    computed_at: str
    status: Literal["ok", "degraded"] = "ok"
    degraded_reason: str | None = None


__all__ = [
    "EdgeConfidence",
    "EdgeRadarItem",
    "EdgeRadarResponse",
    "EdgeSignalType",
    "SimilarPlayerOutcome",
    "SourceHealth",
    "SourceStatus",
]
