from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class LeagueTaxiConfig(BaseModel):
    """Per-league taxi eligibility configuration (D-15). Follows LeagueDraftOrderRule pattern."""

    model_config = ConfigDict(frozen=False)
    taxi_slots: int
    taxi_years_eligible: int
    years_pro_cutoff: int


class LineupSlotScore(BaseModel):
    model_config = ConfigDict(frozen=False)
    position: str
    player_id: str
    player_name: str
    starter_value: float
    replacement_level: float
    score: float


class LineupResult(BaseModel):
    model_config = ConfigDict(frozen=False)
    league_id: str
    roster_id: int
    computed_at: str | None = None
    slot_scores: list[LineupSlotScore]
    total_lineup_score: float
    title_window_label: str
    title_window_composite: float
    ceiling_score: float
    stability_score: float
    depth_score: float


class HygieneSuggestion(BaseModel):
    """Single roster hygiene suggestion (D-10 through D-14)."""

    model_config = ConfigDict(frozen=False)
    action_type: str
    primary_player_ids: list[str]
    primary_player_names: list[str]
    target_player_id: str | None = None
    target_player_name: str | None = None
    counterparty_roster_id: int | None = None
    counterparty_name: str | None = None
    reasoning: str
    direction_fit_score: float


class HygieneResult(BaseModel):
    model_config = ConfigDict(frozen=False)
    league_id: str
    roster_id: int
    computed_at: str | None = None
    suggestions: list[HygieneSuggestion]

    @property
    def consolidate(self) -> list[HygieneSuggestion]:
        return [s for s in self.suggestions if s.action_type == "consolidate"]


class TitleWindowResult(BaseModel):
    """Standalone title-window classification for API response (D-07)."""

    model_config = ConfigDict(frozen=False)
    league_id: str
    roster_id: int
    label: str
    composite: float
    ceiling_score: float
    stability_score: float
    depth_score: float
