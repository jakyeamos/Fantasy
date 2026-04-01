from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FreshnessTag(BaseModel):
    model_config = ConfigDict(frozen=False)

    domain: str
    last_updated: datetime | None
    is_stale: bool
    warning: str | None = None


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
