from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


RiskBand = Literal["Low", "Moderate", "High"]
WarningType = Literal["positional_run", "value_gap"]
TradeVerdictType = Literal["trade", "use"]


class RookiePlayer(BaseModel):
    model_config = ConfigDict(frozen=False)

    player_id: str
    full_name: str
    position: str
    archetype_label: str
    risk_band: RiskBand
    composite_score: float
    tier_number: int
    available_probability_by_slot: dict[str, float] = Field(default_factory=dict)


class RookieTier(BaseModel):
    model_config = ConfigDict(frozen=False)

    tier_number: int
    label: str
    players: list[RookiePlayer]


class RookieBoardResult(BaseModel):
    model_config = ConfigDict(frozen=False)

    league_id: str
    league_format: str
    class_strength_signal: float
    tiers: list[RookieTier]
    computed_at: datetime


class TendencyWarning(BaseModel):
    model_config = ConfigDict(frozen=False)

    warning_type: WarningType
    title: str
    description: str


class TradeVerdict(BaseModel):
    model_config = ConfigDict(frozen=False)

    verdict: TradeVerdictType
    label: str
    reasoning: str


class DraftRoomResult(BaseModel):
    model_config = ConfigDict(frozen=False)

    league_id: str
    pick_slot: int
    pick_slot_display: str
    trade_verdict: TradeVerdict
    best_in_abstract: RookiePlayer | None = None
    tendency_warnings: list[TendencyWarning] = Field(default_factory=list)
