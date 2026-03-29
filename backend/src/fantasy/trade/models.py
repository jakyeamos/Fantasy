from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from fantasy.context.models import RecommendationContext


class TradeAsset(BaseModel):
    model_config = ConfigDict(frozen=False)

    asset_type: Literal["player", "pick"]
    player_id: str | None = None
    pick_owner_roster_id: int | None = None
    pick_year: int | None = None
    pick_round: int | None = None
    projected_slot: str | None = None


class ThirdPartyTrade(BaseModel):
    model_config = ConfigDict(frozen=False)

    roster_id: int
    sends: list[TradeAsset]
    receives: list[TradeAsset]


class DimensionScore(BaseModel):
    model_config = ConfigDict(frozen=False)

    score: float
    confidence: Literal["HIGH", "MEDIUM", "LOW"]
    reasoning: str


class StrategicDistinction(BaseModel):
    model_config = ConfigDict(frozen=False)

    verdict: Literal["advancing", "negative", "neutral"]
    headline: str
    explanation: str


class RerouteResult(BaseModel):
    model_config = ConfigDict(frozen=False)

    reroute_type: Literal["better_target", "better_package", "picks_buyer"]
    headline: str
    reasoning: str
    suggested_assets: list[TradeAsset] | None = None


class PackageOffer(BaseModel):
    model_config = ConfigDict(frozen=False)

    label: str
    send_assets: list[TradeAsset]
    receive_assets: list[TradeAsset]
    reasoning: str


class PackageBuilderResult(BaseModel):
    model_config = ConfigDict(frozen=False)

    aggressive_open: PackageOffer
    fair_close: PackageOffer


class TradeEvaluation(BaseModel):
    model_config = ConfigDict(frozen=False)

    market_fairness: DimensionScore
    roster_fit: DimensionScore
    direction_fit: DimensionScore
    timing_quality: DimensionScore
    insulation_delta: DimensionScore
    liquidity_delta: DimensionScore
    manager_exploit_quality: DimensionScore
    strategic_distinction: StrategicDistinction
    reroutes: list[RerouteResult] | None = None
    package: PackageBuilderResult | None = None
    recommendation_context: RecommendationContext | None = None


class TradeRequest(BaseModel):
    model_config = ConfigDict(frozen=False)

    league_id: str
    user_roster_id: int
    counterparty_roster_id: int | None = None
    user_sends: list[TradeAsset]
    user_receives: list[TradeAsset]
    third_party_trades: list[ThirdPartyTrade] | None = None
    include_reroutes: bool = False
    include_package: bool = False


class PlayerSearchResult(BaseModel):
    model_config = ConfigDict(frozen=False)

    player_id: str
    full_name: str
    position: str
    team: str | None = None
    roster_id: int
    roster_name: str


class PickSearchResult(BaseModel):
    model_config = ConfigDict(frozen=False)

    original_owner_id: int
    current_owner_id: int
    original_owner_name: str
    pick_year: int
    round: int
    projected_slot: str
    current_owner_name: str


class TradeRosterResult(BaseModel):
    model_config = ConfigDict(frozen=False)

    roster_id: int
    roster_name: str
