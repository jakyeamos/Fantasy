from __future__ import annotations

from typing import Any

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
    aggregate_trade_stats: dict[str, Any]
    roster_summary: dict[str, Any] | None = None


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
