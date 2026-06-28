from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from fantasy.context.models import FreshnessTag

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


class TradeSuggestion(BaseModel):
    model_config = ConfigDict(frozen=False)

    league_id: str
    target_player_id: str | None = None
    target_player_name: str | None = None
    target_manager_roster_id: int | None = None
    send_assets: list[str] = Field(default_factory=list)
    receive_assets: list[str] = Field(default_factory=list)
    send_player_ids: list[str] = Field(default_factory=list)
    receive_player_ids: list[str] = Field(default_factory=list)
    fairness_band: Literal["underpay", "fair", "overpay", "unknown"] = "unknown"
    acceptance_confidence: CommandConfidence
    manager_pitch_angle: str
    evaluation_score: float | None = None
    evaluation_verdict: Literal["send", "counter", "avoid", "unknown"] = "unknown"
    evaluation_summary: str | None = None


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
    trade_suggestion: TradeSuggestion | None = None


class DataRefreshAction(BaseModel):
    model_config = ConfigDict(frozen=False)

    id: str
    domain: str
    league_id: str | None = None
    label: str
    description: str
    method: Literal["POST"] = "POST"
    endpoint: str


class CommandCenterResponse(BaseModel):
    model_config = ConfigDict(frozen=False)

    actions: list[CommandAction] = Field(default_factory=list)
    data_health: list[FreshnessTag] = Field(default_factory=list)
    refresh_actions: list[DataRefreshAction] = Field(default_factory=list)
    total: int
    computed_at: str
