from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class WaiverRecommendation(BaseModel):
    model_config = ConfigDict(frozen=False)

    player_id: str
    player_name: str
    position: str
    team: str | None = None
    recommendation_label: Literal["faab_bid", "rolling_waiver", "free_agent_only"]
    bid_low: int | None = None
    bid_mid: int | None = None
    bid_high: int | None = None
    urgency: Literal["High", "Medium", "Low"]
    rationale: str
    is_immediate_start: bool
    data_freshness_warning: bool = False
    hours_since_ingest: float | None = None


class WaiverRecommendationsResponse(BaseModel):
    model_config = ConfigDict(frozen=False)

    league_id: str
    roster_id: int
    waiver_type_label: str
    waiver_type_raw: int
    remaining_faab: int | None = None
    total_faab: int | None = None
    recommendations: list[WaiverRecommendation]
    data_freshness_warning: bool = False
    computed_at: str


class StartupPickValuation(BaseModel):
    model_config = ConfigDict(frozen=False)

    pick_slot: str
    pick_slot_number: int
    projected_player_name: str | None = None
    projected_player_id: str | None = None
    tier_label: str
    trade_up_recommended: bool
    trade_down_recommended: bool
    trade_reasoning: str | None = None
    pick_value: float


class StartupContext(BaseModel):
    model_config = ConfigDict(frozen=False)

    league_id: str
    draft_status: Literal["pre_draft", "drafting", "complete", "unknown"]
    startup_mode_available: bool
    build_template: Literal["win_now", "balanced", "rebuild"]
    direction_label: str
    build_template_hint: str
    pick_valuations: list[StartupPickValuation]
    computed_at: str


class OrphanIntakeDimension(BaseModel):
    model_config = ConfigDict(frozen=False)

    score: float
    label: str
    summary: str


class OrphanIntake(BaseModel):
    model_config = ConfigDict(frozen=False)

    league_id: str
    roster_id: int
    composite_score: float
    composite_label: Literal["Distressed", "Rebuilder", "Balanced", "Ready to Compete"]
    age_curve: OrphanIntakeDimension
    pick_capital: OrphanIntakeDimension
    dead_spots: OrphanIntakeDimension
    lineup_viability: OrphanIntakeDimension
    liquidation_options: OrphanIntakeDimension
    computed_at: str


class ActionPlanItem(BaseModel):
    model_config = ConfigDict(frozen=False)

    priority_rank: int
    category: Literal["add", "drop", "trade", "hold", "evaluate"]
    headline: str
    rationale: str
    urgency: Literal["this_week", "30_days", "offseason"]
    target_entity_type: Literal["player", "pick", "position", "manager"]
    target_entity_ids: list[str]
    confidence_label: Literal["HIGH", "MEDIUM", "LOW"]


class ActionPlan(BaseModel):
    model_config = ConfigDict(frozen=False)

    league_id: str
    roster_id: int
    generated_at: str
    plan_type: Literal["orphan_intake", "startup", "new_connection"]
    items: list[ActionPlanItem]
    summary: str
