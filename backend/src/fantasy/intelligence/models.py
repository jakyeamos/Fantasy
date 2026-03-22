from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class TeamScorecard(BaseModel):
    model_config = ConfigDict(frozen=False)

    league_id: str
    roster_id: int
    computed_at: str | None = None
    win_now: float
    future_value: float
    depth: float
    pick_capital: float
    flexibility: float
    fragility: float
    age_risk: float
    liquidity: float
    positional_insulation: float
    composite: float
    computation_json: str | None = None

    def as_dict(self) -> dict[str, float]:
        return {
            "win_now": self.win_now,
            "future_value": self.future_value,
            "depth": self.depth,
            "pick_capital": self.pick_capital,
            "flexibility": self.flexibility,
            "fragility": self.fragility,
            "age_risk": self.age_risk,
            "liquidity": self.liquidity,
            "positional_insulation": self.positional_insulation,
        }


class DirectionResult(BaseModel):
    model_config = ConfigDict(frozen=False)

    primary_label: str
    confidence: float
    reasoning: str
    alternates: list[dict[str, Any]]
    delta: dict[str, Any]
    approved_moves: list[str]
    discouraged_moves: list[str]


class PlayerValue(BaseModel):
    model_config = ConfigDict(frozen=False)

    league_id: str
    roster_id: int
    player_id: str
    computed_at: str | None = None
    comp_current_production: float | None = None
    comp_short_term: float | None = None
    comp_role_stability: float | None = None
    comp_age_curve: float | None = None
    comp_insulation: float | None = None
    comp_market_liquidity: float | None = None
    comp_positional_scarcity: float | None = None
    comp_fragility: float | None = None
    comp_ceiling: float | None = None
    comp_floor: float | None = None
    comp_rerollability: float | None = None
    comp_contract: float | None = None
    lens_production: float | None = None
    lens_market: float | None = None
    lens_insulation: float | None = None
    lens_team_fit: float | None = None
    lens_direction: float | None = None


class ScorecardInputs(BaseModel):
    model_config = ConfigDict(frozen=False)

    league_id: str
    roster_id: int
    season: int
    roster_positions: list[str]
    starters: list[str]
    bench: list[str]
    ir: list[str]
    taxi: list[str]
    player_ages: dict[str, int]
    player_positions: dict[str, str]
    weekly_fantasy_pts: dict[str, float]
    player_games_played: dict[str, int]
    adp_ranks: dict[str, float]
    pick_rows: list[tuple[str, int, int, str]]
    correction_overrides: dict[str, Any]
    league_settings: dict[str, Any] = {}
    position_medians: dict[str, float] = {}
