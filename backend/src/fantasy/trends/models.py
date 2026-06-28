from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from fantasy.trends.constants import CONFIDENCE_MULTIPLIERS

TrendLabel = Literal["will_rise", "will_maintain", "will_fall"]
TrendConfidence = Literal["HIGH", "MEDIUM", "LOW"]
SuggestedAction = Literal["buy", "sell", "hold"]
CtaDestination = Literal["trade_evaluator", "manager_dossier", "player_rankings"]
OpportunityAvailability = Literal["my_roster", "opponent_roster", "available"]


class TrendResult(BaseModel):
    model_config = ConfigDict(frozen=False)

    player_id: str
    trend_label: TrendLabel
    confidence: TrendConfidence
    delta_magnitude: float
    component_deltas: dict[str, float] = Field(default_factory=dict)
    adp_delta: float | None = None
    seasons_compared: int
    backfilled: bool = False


class SimilarPlayer(BaseModel):
    model_config = ConfigDict(frozen=False)

    player_id: str
    player_name: str
    similarity_score: float
    archetype_label: str | None = None
    context: str


class OpportunityCta(BaseModel):
    model_config = ConfigDict(frozen=False)

    label: str
    destination: CtaDestination
    league_id: str | None = None
    user_roster_id: int | None = None
    manager_roster_id: int | None = None
    target_player_roster_id: int | None = None


class OpportunityWeeklyFit(BaseModel):
    model_config = ConfigDict(frozen=False)

    position: str
    player_name: str
    gap_to_title_target: float
    is_stale: bool = False
    stale_domains: list[str] = Field(default_factory=list)


class OpportunityFeedItem(BaseModel):
    model_config = ConfigDict(frozen=False)

    player_id: str
    player_name: str
    position: str
    trend_label: TrendLabel
    trend_confidence: TrendConfidence
    adp_gap: float
    suggested_action: SuggestedAction
    availability: OpportunityAvailability = "available"
    impact_score: float
    why_summary: str
    owned_in_leagues: list[str] = Field(default_factory=list)
    similar_players: list[SimilarPlayer] = Field(default_factory=list)
    conflict_explanation: str | None = None
    calendar_escalated: bool = False
    calendar_escalation_label: str | None = None
    cta: OpportunityCta | None = None
    weekly_fit: OpportunityWeeklyFit | None = None


class OpportunityFeedResponse(BaseModel):
    model_config = ConfigDict(frozen=False)

    items: list[OpportunityFeedItem] = Field(default_factory=list)
    total: int
    computed_at: str
    status: Literal["ok", "degraded"] = "ok"
    degraded_reason: str | None = None


def confidence_multiplier(confidence: TrendConfidence) -> float:
    return float(CONFIDENCE_MULTIPLIERS.get(confidence, 0.4))


def trend_to_supporting_factor(trend: TrendResult) -> dict[str, str | float]:
    direction_map: dict[TrendLabel, Literal["positive", "negative", "neutral"]] = {
        "will_rise": "positive",
        "will_fall": "negative",
        "will_maintain": "neutral",
    }
    movement_map: dict[TrendLabel, str] = {
        "will_rise": "rise",
        "will_fall": "fall",
        "will_maintain": "remain stable",
    }
    magnitude = round(abs(trend.delta_magnitude) * confidence_multiplier(trend.confidence), 2)
    explanation = (
        f"Component scores project a {movement_map[trend.trend_label]} next season "
        f"({trend.seasons_compared} season{'s' if trend.seasons_compared != 1 else ''} compared"
        f"{', backfilled' if trend.backfilled else ''})."
    )
    return {
        "factor_name": "Value Trend",
        "direction": direction_map[trend.trend_label],
        "magnitude": max(magnitude, 0.0),
        "explanation": explanation,
    }
