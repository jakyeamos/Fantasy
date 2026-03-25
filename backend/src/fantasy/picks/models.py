"""Pydantic domain models for Phase 6 pick valuation.

PickValuationContext includes the class_strength_signal field as a Phase 7 injection hook.
Phase 6 always passes 0.0 (neutral). Phase 7 injects a real value without touching engine code.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from fantasy.picks.constants import DraftTiebreaker, NonPlayoffOrderBasis, PlayoffOrdering
from fantasy.trade.models import TradeAsset


class TimingLabel(str, Enum):
    SELL_NOW = "sell_now"
    HOLD_UNTIL_ROOKIE_FEVER = "hold_until_rookie_fever"
    USE_ON_THE_CLOCK = "use_on_the_clock"


class TeamStandingsRow(BaseModel):
    model_config = ConfigDict(frozen=False)

    roster_id: int
    wins: int
    losses: int
    win_pct: float = Field(ge=0.0, le=1.0)
    remaining_games: int = Field(ge=0)
    recent_wins: int = Field(ge=0)
    total_games: int = Field(ge=0)
    draft_in_progress: bool = False


class LeaguePickContext(BaseModel):
    model_config = ConfigDict(frozen=False)

    league_id: str
    league_size: int = Field(ge=2)
    rebuilder_count: int = Field(ge=0)
    rebuilder_ratio: float = Field(ge=0.0, le=1.0)
    total_teams: int = Field(ge=1)


class LeagueDraftOrderRule(BaseModel):
    model_config = ConfigDict(frozen=False)

    non_playoff_basis: NonPlayoffOrderBasis
    playoff_ordering: PlayoffOrdering
    tiebreaker: DraftTiebreaker


class PickValuationContext(BaseModel):
    model_config = ConfigDict(frozen=False)

    # The pick being valued — uses TradeAsset with asset_type='pick'
    pick: TradeAsset
    league_id: str
    draft_order_rule: LeagueDraftOrderRule | None = Field(
        default=None,
        description="Phase 10: rule-aware slot projection. None = blocked state per D-01.",
    )

    # Phase 7 injects here — Phase 6 always passes 0.0
    class_strength_signal: float = Field(
        default=0.0,
        description=(
            "Class strength deviation from neutral. Injected by Phase 7. "
            "Range: -1.0 (historically weak class) to +1.0 (historically strong). "
            "Phase 6 hardcodes 0.0 (neutral)."
        ),
        ge=-1.0,
        le=1.0,
    )

    # Pre-computed demand factor for the target manager (0.0–1.0)
    target_manager_demand_factor: float = Field(default=0.5, ge=0.0, le=1.0)


class PickValue(BaseModel):
    model_config = ConfigDict(frozen=False)

    pick: TradeAsset
    base_value: float = Field(ge=0.0)
    timed_value: float = Field(ge=0.0)
    league_adjusted_value: float = Field(ge=0.0)
    demand_adjusted_value: float = Field(ge=0.0)
    expected_draft_slot: float = Field(ge=1.0)
    timing_label: TimingLabel
    timing_reasoning: str
    class_strength_signal: float = Field(ge=-1.0, le=1.0)
    years_out: int = Field(default=0, ge=0)
    computed_at: datetime
    rule_citation: str | None = Field(
        default=None,
        description=(
            "Backend-rendered citation string, e.g. 'Using: Max points for · Playoff teams by finish'. "
            "None = rule not configured; frontend renders blocked state per D-02."
        ),
    )
