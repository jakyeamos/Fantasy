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


class CommandCenterResponse(BaseModel):
    model_config = ConfigDict(frozen=False)

    actions: list[CommandAction] = Field(default_factory=list)
    total: int
    computed_at: str
