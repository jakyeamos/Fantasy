from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProspectFeatures(BaseModel):
    model_config = ConfigDict(frozen=False)

    player_id: str
    player_name: str
    position: str
    draft_year: int
    age_at_draft: float | None = None
    draft_ovr: int | None = None
    forty: float | None = None
    weight: float | None = None
    height: float | None = None
    vertical: float | None = None
    bench: int | None = None
    cone: float | None = None
    shuttle: float | None = None
    college_games: int | None = None
    college_targets: float | None = None
    college_receptions: float | None = None
    college_receiving_yards: float | None = None
    college_receiving_tds: float | None = None
    college_routes_run: float | None = None
    college_carries: float | None = None
    college_rushing_yards: float | None = None
    college_rushing_tds: float | None = None
    college_pass_attempts: float | None = None
    college_completions: float | None = None
    college_passing_yards: float | None = None
    college_passing_tds: float | None = None
    college_interceptions: float | None = None
    college_rec_ypg: float | None = None
    college_rush_ypg: float | None = None
    college_yprr: float | None = None
    college_ypt: float | None = None
    college_ypc: float | None = None
    college_ypa: float | None = None
    college_pass_td_rate: float | None = None
    college_qb_rush_yards: float | None = None
    college_qb_rush_tds: float | None = None
    college_qb_rush_ypg: float | None = None
    college_scramble_rate: float | None = None
    college_mkt_share_proxy: float | None = None
    college_td_rate: float | None = None
    college_completion_pct_proxy: float | None = None
    adp: float | None = None
    archetype_label: str | None = None
    outcome_bucket: str | None = None


class HistoricalComp(BaseModel):
    model_config = ConfigDict(frozen=False)

    player_id: str
    player_name: str
    role: Literal["ceiling", "median", "floor"]
    outcome_bucket: Literal["hit", "mediocre", "bust"]
    match_reason: str


class SubFlag(BaseModel):
    model_config = ConfigDict(frozen=False)

    signal_name: str
    direction: Literal["positive", "negative", "neutral"]
    magnitude_str: str


class ProspectModelOutput(BaseModel):
    model_config = ConfigDict(frozen=False)

    league_id: str = "__global__"
    draft_season: int
    player_id: str
    player_name: str
    position: str
    archetype_label: str
    hit_rate_bucket: str
    tier: int
    predicted_tier: int
    predicted_bucket: str
    risk_band: str
    comps: list[HistoricalComp] = Field(default_factory=list)
    overvalue_flag_direction: Literal["overvalued", "undervalued"] | None = None
    overvalue_magnitude: int | None = None
    low_confidence: bool = False
    sub_flags: list[SubFlag] = Field(default_factory=list)
    computed_at: datetime
