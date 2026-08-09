from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FreshnessTag(BaseModel):
    model_config = ConfigDict(frozen=False)

    domain: str
    last_updated: datetime | None
    fetched_at: datetime | None = None
    observed_at: datetime | None = None
    effective_at: datetime | None = None
    coverage_through: datetime | None = None
    status: str = "unknown"
    source_id: str | None = None
    record_count: int | None = None
    is_stale: bool
    warning: str | None = None


class EvidenceFreshness(BaseModel):
    model_config = ConfigDict(frozen=False)

    is_stale: bool = False
    stale_domains: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CalendarContext(BaseModel):
    model_config = ConfigDict(frozen=False)

    active_state: str
    detected_at: datetime


class RecommendationContext(BaseModel):
    model_config = ConfigDict(frozen=False)

    calendar_state: str
    freshness_tags: list[FreshnessTag] = []
    calendar_note: str | None = None


class FreshnessRow(BaseModel):
    model_config = ConfigDict(frozen=False)

    league_id: str
    domain: str
    last_updated: datetime | None
    notes: str | None = None
    fetched_at: datetime | None = None
    observed_at: datetime | None = None
    effective_at: datetime | None = None
    coverage_through: datetime | None = None
    status: str = "unknown"
    source_id: str | None = None
    record_count: int | None = None
