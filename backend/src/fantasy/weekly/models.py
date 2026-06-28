from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class WeeklyPlayerSignal(BaseModel):
    model_config = ConfigDict(frozen=False)

    player_id: str
    player_name: str
    position: str
    team: str | None = None
    roster_slot: Literal["starter", "bench"]
    recent_points: float
    recent_opportunities: float
    injury_status: str | None = None
    availability_warning: str | None = None


class StartSitDecision(BaseModel):
    model_config = ConfigDict(frozen=False)

    start_player_id: str
    start_player_name: str
    sit_player_id: str
    sit_player_name: str
    position: str
    edge_points: float
    confidence: Literal["HIGH", "MEDIUM", "LOW"]
    recommendation: str
    why_now: str
    risk_if_wrong: str
    stale_domains: list[str] = Field(default_factory=list)


class LineupGapDecision(BaseModel):
    model_config = ConfigDict(frozen=False)

    position: str
    current_player_id: str
    current_player_name: str
    gap_to_title_target: float
    gap_to_playoff_target: float
    recommended_action: str
    urgency: Literal["today", "this_week", "watch", "low"]
    confidence: Literal["HIGH", "MEDIUM", "LOW"]
    why_now: str
    stale_domains: list[str] = Field(default_factory=list)


class WeeklyEdgeResponse(BaseModel):
    model_config = ConfigDict(frozen=False)

    league_id: str
    roster_id: int
    computed_at: str
    player_signals: list[WeeklyPlayerSignal] = Field(default_factory=list)
    start_sit: list[StartSitDecision] = Field(default_factory=list)
    lineup_gaps: list[LineupGapDecision] = Field(default_factory=list)
    stale_domains: list[str] = Field(default_factory=list)

