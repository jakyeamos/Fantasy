from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


DraftSelectionType = Literal["startup", "rookie"]


class DraftPickSelection(BaseModel):
    model_config = ConfigDict(frozen=False)

    league_id: str
    draft_id: str
    roster_id: int
    player_id: str
    pick_slot: int
    round_number: int
    season: int
    draft_type: DraftSelectionType
    position: str | None = None
    archetype_label: str | None = None


class RookiePickProfile(BaseModel):
    model_config = ConfigDict(frozen=False)

    league_id: str
    roster_id: int
    computed_at: str
    pick_premium_score: float | None = None
    pick_trade_evidence: int = 0
    draft_selection_count: int = 0
    positional_tendency: dict[str, float] = {}
    dominant_archetype: str | None = None
    archetype_pattern: dict[str, int] = {}
    show_draft_picks_tab: bool = False
    draft_selection_history: list[dict] = []

