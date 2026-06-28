from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ExposureRow(BaseModel):
    model_config = ConfigDict(frozen=False)

    player_id: str
    full_name: str
    position: str
    team: str | None = None
    owned_in_leagues: list[str] = Field(default_factory=list)
    league_count: int
    hedge_rec: str | None = None
    urgency: Literal["sell", "hold", "hedge", "monitor"] = "monitor"
    urgency_reason: str | None = None


class CorrelatedRiskPlayer(BaseModel):
    model_config = ConfigDict(frozen=False)

    player_id: str
    full_name: str
    league_id: str


class CorrelatedRiskRow(BaseModel):
    model_config = ConfigDict(frozen=False)

    nfl_team: str
    players: list[CorrelatedRiskPlayer] = Field(default_factory=list)
    league_ids: list[str] = Field(default_factory=list)
    risk_string: str = ""


class SnapshotAnchor(BaseModel):
    model_config = ConfigDict(frozen=False)

    snapshot_id: int
    snapshot_at: datetime
    anchor_type: Literal["trade", "roster_change", "season_start", "season_end"]
    label: str


class DiffRow(BaseModel):
    model_config = ConfigDict(frozen=False)

    field: str
    field_type: Literal[
        "direction_label",
        "scorecard",
        "player_value",
        "pick_capital",
        "departed",
        "added",
    ]
    delta: float | None = None
    old_value: str | None = None
    new_value: str | None = None
    display_string: str


class RetroGrade(BaseModel):
    model_config = ConfigDict(frozen=False)

    run_type: Literal["direction_labels", "prospect_tiers", "full"]
    season: str
    grades_json: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None


class RecalibrationHealth(BaseModel):
    model_config = ConfigDict(frozen=False)

    last_recalibrated_at: datetime | None = None


class PortfolioExposureResponse(BaseModel):
    model_config = ConfigDict(frozen=False)

    exposure: list[ExposureRow] = Field(default_factory=list)
    correlated_risk: list[CorrelatedRiskRow] = Field(default_factory=list)
