from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CommandCategory = Literal[
    "waiver",
    "lineup",
    "trade",
    "market",
    "rookie_pick",
    "portfolio",
    "manager",
]
CommandUrgency = Literal["today", "this_week", "watch", "low"]
CommandConfidence = Literal["HIGH", "MEDIUM", "LOW"]


class CommandAction(BaseModel):
    model_config = ConfigDict(frozen=False)

    id: str
    league_id: str | None = None
    roster_id: int | None = None
    category: CommandCategory
    priority_rank: int
    urgency: CommandUrgency
    confidence: CommandConfidence
    headline: str
    recommended_action: str
    why_now: str
    risk_if_wrong: str
    evidence: list[str] = Field(default_factory=list)
    cta_label: str
    cta_destination: str
    stale_domains: list[str] = Field(default_factory=list)


class CommandCenterResponse(BaseModel):
    model_config = ConfigDict(frozen=False)

    actions: list[CommandAction] = Field(default_factory=list)
    total: int
    computed_at: str

