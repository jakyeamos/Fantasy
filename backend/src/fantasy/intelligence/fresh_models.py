from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class SourceTier(StrEnum):
    STRUCTURED = "structured"
    OFFICIAL = "official"
    PUBLIC = "public"
    BROWSER = "browser"


class ParseStatus(StrEnum):
    PARSED = "parsed"
    EMPTY = "empty"
    UNAVAILABLE = "unavailable"
    BLOCKED = "blocked"
    MANUAL_REVIEW = "manual_review"


class EventType(StrEnum):
    INJURY_STATUS = "injury_status"
    PRACTICE_PARTICIPATION = "practice_participation"
    RESERVE_TRANSACTION = "reserve_transaction"
    ROSTER_TRANSACTION = "roster_transaction"
    DEPTH_CHART_ROLE = "depth_chart_role"
    USAGE_SHIFT = "usage_shift"
    MARKET_VALUE_CHANGE = "market_value_change"


class VerificationState(StrEnum):
    CONFIRMED = "confirmed"
    WATCH = "watch"
    CONFLICTED = "conflicted"
    EXPIRED = "expired"
    MANUAL_REVIEW = "manual_review"


class SourceObservation(BaseModel):
    model_config = ConfigDict(frozen=True)

    observation_id: str
    run_id: str
    source_id: str
    source_tier: SourceTier
    url: str | None = None
    fetched_at: datetime
    observed_at: datetime | None = None
    effective_at: datetime | None = None
    coverage_through: datetime | None = None
    content_hash: str
    parse_status: ParseStatus
    evidence_excerpt: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    authoritative: bool = False
    model_extracted: bool = False


class ExtractedEventClaim(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_type: EventType
    player_id: str | None = None
    player_name: str | None = None
    team: str | None = None
    effective_at: datetime | None = None
    expires_at: datetime | None = None
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)
    evidence_start: int | None = None
    evidence_end: int | None = None


class FootballEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: str
    fingerprint: str
    subject_key: str
    event_type: EventType
    player_id: str | None = None
    player_name: str | None = None
    team: str | None = None
    effective_at: datetime | None = None
    observed_at: datetime
    expires_at: datetime | None = None
    verification_state: VerificationState
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)
    observation_ids: list[str] = Field(default_factory=list)


class ImpactSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    affected_asset_ids: list[str] = Field(default_factory=list)
    before: dict[str, Any] = Field(default_factory=dict)
    after: dict[str, Any] = Field(default_factory=dict)
    deltas: dict[str, float] = Field(default_factory=dict)


class LeagueImpact(BaseModel):
    model_config = ConfigDict(frozen=True)

    impact_id: str
    event_id: str
    league_id: str
    roster_id: int | None = None
    impact_type: str
    headline: str
    explanation: str
    impact_summary: ImpactSummary
    confidence: float = Field(ge=0.0, le=1.0)
    actionable: bool = False
    recommended_action: str | None = None
    cta_label: str | None = None
    cta_destination: str | None = None
    invalidation: str
    model_version: str
    computed_at: datetime


class SourceOutcome(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str
    status: Literal["complete", "partial", "failed", "skipped"]
    records_seen: int = 0
    observations_written: int = 0
    events_written: int = 0
    fetched_at: datetime | None = None
    coverage_through: datetime | None = None
    message: str | None = None


class BriefItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    item_id: str
    event_id: str
    league_id: str | None = None
    roster_id: int | None = None
    lane: Literal["changed", "best_move", "watch"]
    priority_rank: int
    headline: str
    why_it_matters: str
    recommended_action: str | None = None
    confidence: float
    source_summary: str
    invalidation: str
    impact_summary: ImpactSummary = Field(default_factory=ImpactSummary)
    cta_label: str | None = None
    cta_destination: str | None = None


class MorningBrief(BaseModel):
    model_config = ConfigDict(frozen=True)

    brief_id: str
    brief_date: date
    run_id: str
    status: Literal["ready", "degraded", "empty"]
    created_at: datetime
    items: list[BriefItem] = Field(default_factory=list)
    source_health: list[SourceOutcome] = Field(default_factory=list)


class IntelligenceRunResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    status: Literal["complete", "degraded", "failed"]
    source_outcomes: list[SourceOutcome] = Field(default_factory=list)
    event_count: int = 0
    impact_count: int = 0
    brief_id: str | None = None


class AnalyzeUrlRequest(BaseModel):
    url: HttpUrl


class EventReviewRequest(BaseModel):
    decision: Literal["confirm", "reject"]
    notes: str | None = Field(default=None, max_length=1000)


class BriefFeedbackRequest(BaseModel):
    verdict: Literal["acted", "useful", "not_relevant", "dismissed"]
    notes: str | None = Field(default=None, max_length=1000)


class RefreshRequest(BaseModel):
    league_ids: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    scheduled: bool = False


class EventDetail(BaseModel):
    event: FootballEvent
    observations: list[SourceObservation] = Field(default_factory=list)
    impacts: list[LeagueImpact] = Field(default_factory=list)


class AnalyzeUrlResponse(BaseModel):
    run_id: str
    url: str
    retrieval: Literal["http", "browser"]
    events: list[FootballEvent] = Field(default_factory=list)
    impacts: list[LeagueImpact] = Field(default_factory=list)


__all__ = [
    "AnalyzeUrlRequest",
    "AnalyzeUrlResponse",
    "BriefFeedbackRequest",
    "BriefItem",
    "EventReviewRequest",
    "EventDetail",
    "EventType",
    "ExtractedEventClaim",
    "FootballEvent",
    "ImpactSummary",
    "IntelligenceRunResult",
    "LeagueImpact",
    "MorningBrief",
    "ParseStatus",
    "RefreshRequest",
    "SourceObservation",
    "SourceOutcome",
    "SourceTier",
    "VerificationState",
]
