from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from fantasy.trust.constants import RuleSupportLevel


class RuleScanEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    rule: str
    support_level: RuleSupportLevel
    reason: str
    distorts_recommendations: bool


class LeagueFormatScan(BaseModel):
    model_config = ConfigDict(frozen=True)

    league_id: str
    entries: list[RuleScanEntry]
    needs_acknowledgment: bool
    league_unsupported: bool


class FormatAcknowledgment(BaseModel):
    model_config = ConfigDict(frozen=False)

    league_id: str
    acknowledged_rules: list[str]
    acknowledged_at: str

