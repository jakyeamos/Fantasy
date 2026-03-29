from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class PitchAngle(BaseModel):
    model_config = ConfigDict(frozen=False)

    rank: int
    deal_archetype: str
    send_description: str
    avoid_description: str
    reasoning: str


class ExploitationClassification(BaseModel):
    model_config = ConfigDict(frozen=False)

    primary_type: str | None = None
    secondary_type: str | None = None
    evidence_strings: dict[str, str]
    evidence_counts: dict[str, int] = {}
    metadata: dict[str, Any] = {}


class ManagerProfile(BaseModel):
    model_config = ConfigDict(frozen=False)

    league_id: str
    roster_id: int
    computed_at: str
    manager_name: str | None = None
    direction_label: str | None = None
    evidence_count: int
    low_confidence: bool
    exploitability_score: float
    exploitation_primary: str | None = None
    exploitation_secondary: str | None = None
    exploitation_evidence: dict[str, str]
    pitch_angles: list[PitchAngle]
    trade_history: list[dict[str, Any]] = []
    aggregate_trade_stats: dict[str, Any]
    roster_summary: dict[str, Any] | None = None
    pick_premium_score: float | None = None
    pick_trade_evidence: int = 0
    draft_selection_count: int = 0
    positional_tendency: dict[str, float] = {}
    dominant_archetype: str | None = None
    archetype_pattern: dict[str, int] = {}
    show_draft_picks_tab: bool = False
    draft_selection_history: list[dict] = []
    likely_motivations_now: str | None = None
    recent_urgency_state: Literal[
        "building_urgency",
        "stable",
        "declining_window",
        "panic_mode",
    ] | None = None
    time_of_calendar_sensitivity: float = 0.0
    veteran_appetite: float = 0.0
    rookie_fever_index: float = 0.0
    value_rigidity: float = 0.0
    reroute_susceptibility: float = 0.0
    best_asset_to_target: str | None = None
    best_asset_to_send: str | None = None


class ManagerSummary(BaseModel):
    model_config = ConfigDict(frozen=False)

    league_id: str
    roster_id: int
    manager_name: str
    direction_label: str | None = None
    exploitability_score: float
    evidence_count: int
    low_confidence: bool
    top_pitch_angle: PitchAngle | None = None
    pick_premium_score: float | None = None
