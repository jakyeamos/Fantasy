from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from fantasy.context.models import RecommendationContext
from fantasy.recommendation.models import RecommendationCard


class TradeAsset(BaseModel):
    model_config = ConfigDict(frozen=False)

    asset_type: Literal["player", "pick"]
    player_id: str | None = None
    pick_owner_roster_id: int | None = None
    pick_year: int | None = None
    pick_round: int | None = None
    projected_slot: str | None = None
    label: str | None = None


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


class ThirdPartyTradeEvaluation(BaseModel):
    model_config = ConfigDict(frozen=False)

    roster_id: int
    sent_market_value: float
    received_market_value: float
    net_market_delta: float
    market_fairness: DimensionScore


class TradeBalance(BaseModel):
    model_config = ConfigDict(frozen=False)

    sent_raw_value: float
    received_raw_value: float
    sent_adjusted_value: float
    received_adjusted_value: float
    net_adjusted_delta: float
    fairness_score: float
    package_quality_note: str


class RerouteResult(BaseModel):
    model_config = ConfigDict(frozen=False)

    reroute_type: Literal["better_target", "better_package", "picks_buyer"]
    headline: str
    reasoning: str
    suggested_assets: list[TradeAsset] | None = None
    target_roster_id: int | None = None
    target_label: str | None = None


class PackageOffer(BaseModel):
    model_config = ConfigDict(frozen=False)

    label: str
    send_assets: list[TradeAsset]
    receive_assets: list[TradeAsset]
    reasoning: str


class ParticipantPackageOffer(BaseModel):
    model_config = ConfigDict(frozen=False)

    roster_id: int
    role: Literal["user", "primary_counterparty", "third_party"]
    label: str
    send_assets: list[TradeAsset]
    receive_assets: list[TradeAsset]
    reasoning: str
    market_fairness: DimensionScore | None = None


class TradeAnalysisAsset(BaseModel):
    model_config = ConfigDict(frozen=False)

    side: Literal[
        "user_send",
        "user_receive",
        "counterparty_send",
        "counterparty_receive",
    ]
    asset: TradeAsset
    label: str
    position: str | None = None
    age: int | None = None
    current_owner_roster_id: int | None = None
    current_owner_name: str | None = None
    original_owner_name: str | None = None
    market_value: float | None = None
    context_value: float | None = None
    valuation_source: str
    evidence_status: Literal["available", "degraded", "unavailable"]
    evidence_notes: list[str] = Field(default_factory=list)


class TradeLineupImpact(BaseModel):
    model_config = ConfigDict(frozen=False)

    roster_id: int
    roster_name: str
    status: Literal["available", "degraded", "unavailable"]
    before_title_window: str | None = None
    after_title_window: str | None = None
    before_score: float | None = None
    after_score: float | None = None
    score_delta: float | None = None
    starter_changes: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class TradeAnalysisOffer(BaseModel):
    model_config = ConfigDict(frozen=False)

    label: str
    send_assets: list[TradeAsset]
    receive_assets: list[TradeAsset]
    purpose: Literal["current", "aggressive_open", "preferred_close", "fallback", "walk_away"]
    rationale: str


class TradeAnalysisScenario(BaseModel):
    model_config = ConfigDict(frozen=False)

    label: str
    scenario_type: Literal[
        "current_offer",
        "aggressive_open",
        "preferred_close",
        "fallback",
        "walk_away",
    ]
    score_low: float | None = None
    score_high: float | None = None
    score_point: float | None = None
    verdict: Literal["accept", "counter", "hold", "walk_away"]
    rationale: str
    assumptions: list[str] = Field(default_factory=list)


class TradeNegotiationLadder(BaseModel):
    model_config = ConfigDict(frozen=False)

    aggressive_open: TradeAnalysisOffer
    preferred_close: TradeAnalysisOffer
    fallback: TradeAnalysisOffer
    walk_away: TradeAnalysisOffer
    walk_away_rule: str


class TradeAnalysisQuality(BaseModel):
    model_config = ConfigDict(frozen=False)

    completeness_score: float
    evidence_reliability_score: float
    status: Literal["complete", "complete_with_degraded_evidence", "blocked"]
    gates: dict[str, bool]
    limitations: list[str] = Field(default_factory=list)
    freshness: dict[str, object] = Field(default_factory=dict)
    calibration: dict[str, object] = Field(default_factory=dict)


class TradeFollowUpEvent(BaseModel):
    model_config = ConfigDict(frozen=False)

    id: int
    created_at: str
    event_type: str
    action_taken: str | None = None
    outcome: str | None = None
    outcome_score: float | None = None
    follow_up_at: str | None = None
    resolution_state: str
    notes: str | None = None
    recommendation_action: str
    confidence: float


class TradeCalibrationEvidence(BaseModel):
    model_config = ConfigDict(frozen=False)

    status: Literal["available", "unavailable"]
    win_probability_status: Literal["available", "unavailable"]
    league_id: str
    league_name: str | None = None
    decision_type: Literal["trade"] = "trade"
    sample_size: int
    minimum_sample_size: int
    captured_decisions: int
    progress_percent: float
    message: str
    model_name: str | None = None
    model_version: str | None = None
    metrics: dict[str, object] | None = None


class TradeFollowUpRow(BaseModel):
    model_config = ConfigDict(frozen=False)

    decision_id: str
    presentation_id: int
    league_id: str
    roster_id: int
    question: str | None = None
    recommendation_action: str
    confidence: float
    latest_event: str
    resolution_state: str
    follow_up_at: str | None = None
    is_due: bool
    history: list[TradeFollowUpEvent] = Field(default_factory=list)


class TradeFollowUpsResponse(BaseModel):
    model_config = ConfigDict(frozen=False)

    schema_version: Literal["trade-followups/1.0"] = "trade-followups/1.0"
    league_id: str
    league_name: str | None = None
    calibration: TradeCalibrationEvidence
    follow_ups: list[TradeFollowUpRow] = Field(default_factory=list)


class TradeFollowUpEventRequest(BaseModel):
    model_config = ConfigDict(frozen=False)

    event_type: Literal["accepted", "rejected", "held", "outcome"]
    outcome: Literal["recommendation_correct", "recommendation_incorrect"] | None = None
    follow_up_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=500)


class TradeFollowUpEventResponse(BaseModel):
    model_config = ConfigDict(frozen=False)

    schema_version: Literal["trade-feedback-event/1.0"] = "trade-feedback-event/1.0"
    decision_id: str
    event_id: int
    event_type: str
    resolution_state: str
    follow_up_at: str | None = None
    calibration: TradeCalibrationEvidence


class TradeFeedbackLink(BaseModel):
    model_config = ConfigDict(frozen=False)

    decision_id: str
    presentation_id: int
    latest_event: str
    resolution_state: str
    follow_up_at: str | None = None


class TradeAnalysis(BaseModel):
    model_config = ConfigDict(frozen=False)

    schema_version: str = "trade-analysis/1.0"
    headline: str
    verdict: Literal["accept", "counter", "hold", "walk_away"]
    model_score_low: float
    model_score_high: float
    model_score_point: float
    score_interpretation: str
    assets: list[TradeAnalysisAsset]
    lineup_impacts: list[TradeLineupImpact]
    scenarios: list[TradeAnalysisScenario]
    negotiation: TradeNegotiationLadder
    quality: TradeAnalysisQuality
    key_reasons: list[str] = Field(default_factory=list)
    contrary_case: str
    what_changes_the_answer: list[str] = Field(default_factory=list)


class PackageBuilderResult(BaseModel):
    model_config = ConfigDict(frozen=False)

    aggressive_open: PackageOffer
    fair_close: PackageOffer
    roster_fit_counter: PackageOffer | None = None
    participant_offers: list[ParticipantPackageOffer] | None = None


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
    trade_balance: TradeBalance | None = None
    third_party_evaluations: list[ThirdPartyTradeEvaluation] | None = None
    recommendation_context: RecommendationContext | None = None
    recommendation_cards: list[RecommendationCard] | None = None
    trade_analysis: TradeAnalysis | None = None
    feedback: TradeFeedbackLink | None = None
    degradation_reasons: list[str] = Field(default_factory=list)


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


class HistoricalAsset(BaseModel):
    model_config = ConfigDict(frozen=False)

    asset_type: Literal["player", "pick"]
    label: str
    player_id: str | None = None
    player_position: str | None = None
    pick_year: int | None = None
    pick_round: int | None = None
    pick_original_roster_id: int | None = None


class HistoricalTradeParticipant(BaseModel):
    model_config = ConfigDict(frozen=False)

    roster_id: int
    roster_name: str
    sends: list[HistoricalAsset]
    receives: list[HistoricalAsset]
    current_replay: TradeEvaluation | None = None
    current_replay_error: str | None = None
    at_time_status: Literal["available", "unavailable"]
    at_time_delta: float | None = None
    at_time_note: str


class HistoricalTradeEvaluationRow(BaseModel):
    model_config = ConfigDict(frozen=False)

    transaction_id: str
    date: str | None
    week: int | None
    participant_roster_ids: list[int]
    participants: list[HistoricalTradeParticipant]
    summary: str
    current_winner_roster_id: int | None = None
    current_winner_name: str | None = None
    current_best_delta: float | None = None
    at_time_status: Literal["available", "unavailable"]
    at_time_note: str


class LeagueTradeHistoryResponse(BaseModel):
    model_config = ConfigDict(frozen=False)

    league_id: str
    trades: list[HistoricalTradeEvaluationRow]
