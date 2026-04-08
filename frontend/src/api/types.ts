export type DirectionReadBand = "Clear" | "Leaning" | "Hybrid" | "Tentative" | "--"

export interface DashboardLeagueSummary {
  league_id: string
  league_name: string
  user_roster_id: number | null
  direction_label: string
  confidence_band: "High" | "Medium" | "Low" | "--"
  direction_read: DirectionReadBand
  direction_alternates: string[]
  direction_note: string | null
  summary_signal: string
  primary_weakness: string
  top_exploit_window: string | null
  last_snapshot_at: string | null
  last_ingest_at: string | null
}

export interface SnapshotStatus {
  league_id: string
  last_snapshot_at: string | null
}

export interface SnapshotTriggerResponse {
  snapshot_ids: number[]
  count: number
}

export interface RiserFallerEntry {
  player_name: string
  delta: number
  reason: string
}

export interface ExploitTrigger {
  type: string
  description: string
  suggested_action: string
}

export interface ExploitWindowManager {
  roster_id: number
  manager_name?: string | null
  trigger_count: number
  is_high_opportunity: boolean
  triggers: ExploitTrigger[]
}

export interface DirectionFitFlag {
  dimension: string
  label: string
  strength: "Strong Fit" | "Supporting" | "Secondary"
  detail: string
}

export interface ComparativeMetricSummary {
  key: "win_now" | "future_value" | "title_window"
  label: string
  rank: number
  league_size: number
  score: number
  gap_to_leader: number
  edge_vs_median: number
}

export interface PowerRankingEntry {
  roster_id: number
  manager_name: string
  rank: number
  score: number
  is_user: boolean
  direction_label: string | null
  title_window_label: string | null
  record: string | null
}

export interface MatchupPrediction {
  roster_id: number
  manager_name: string
  win_probability: number
  verdict: "favored" | "toss_up" | "underdog"
  reason: string
}

export interface LeagueCompetitiveLandscape {
  metric_summaries: ComparativeMetricSummary[]
  win_now_rankings: PowerRankingEntry[]
  future_value_rankings: PowerRankingEntry[]
  title_window_rankings: PowerRankingEntry[]
  matchup_predictions: MatchupPrediction[]
}

export interface LeagueDetailResponse {
  league_id: string
  league_name: string
  user_roster_id: number | null
  user_roster_name: string | null
  user_owner_id: string | null
  user_roster_player_ids: string[]
  direction_label: string
  confidence_band: "High" | "Medium" | "Low" | "--"
  direction_read: DirectionReadBand
  direction_alternates: string[]
  direction_note: string | null
  direction_reasoning: string | null
  direction_fit_flags: DirectionFitFlag[]
  primary_weakness: string
  risers: RiserFallerEntry[]
  fallers: RiserFallerEntry[]
  exploit_windows: ExploitWindowManager[]
  last_snapshot_at: string | null
  last_ingest_at: string | null
  recommendation_context?: RecommendationContext | null
  competitive_landscape?: LeagueCompetitiveLandscape | null
}

export interface LeagueRosterOption {
  roster_id: number
  owner_id: string | null
  owner_display_name: string | null
  wins: number
  losses: number
  ties: number
  points_for: number
}

export interface PitchAngle {
  rank: number
  deal_archetype: string
  send_description: string
  avoid_description: string
  reasoning: string
}

export interface ManagerSummary {
  league_id: string
  roster_id: number
  manager_name: string
  direction_label: string | null
  exploitability_score: number
  evidence_count: number
  low_confidence: boolean
  top_pitch_angle: PitchAngle | null
  pick_premium_score?: number | null
}

export interface TradeHistoryEntry {
  transaction_id: string
  date: string | null
  sent_assets: string[]
  received_assets: string[]
  value_delta: number
}

export interface ManagerProfile {
  league_id: string
  roster_id: number
  computed_at: string
  manager_name: string | null
  direction_label: string | null
  evidence_count: number
  low_confidence: boolean
  exploitability_score: number
  exploitation_primary: string | null
  exploitation_secondary: string | null
  exploitation_evidence: Record<string, string>
  pitch_angles: PitchAngle[]
  trade_history: TradeHistoryEntry[]
  aggregate_trade_stats: {
    total_trades: number
    win_rate: number
    avg_delta: number
  }
  roster_summary: {
    manager_name?: string
    direction_label?: string | null
    positional_needs?: string[]
    roster_size?: number
  } | null
  pick_premium_score?: number | null
  pick_trade_evidence?: number
  draft_selection_count?: number
  positional_tendency?: Record<string, number>
  dominant_archetype?: string | null
  archetype_pattern?: Record<string, number>
  show_draft_picks_tab?: boolean
  draft_selection_history?: Array<{
    player_id: string
    pick_slot: number
    round_number: number
    season: number
    draft_type: "startup" | "rookie"
    position: string | null
    archetype_label: string | null
  }>
  likely_motivations_now?: string | null
  recent_urgency_state?:
    | "building_urgency"
    | "stable"
    | "declining_window"
    | "panic_mode"
    | null
  time_of_calendar_sensitivity?: number
  veteran_appetite?: number
  rookie_fever_index?: number
  value_rigidity?: number
  reroute_susceptibility?: number
  best_asset_to_target?: string | null
  best_asset_to_send?: string | null
}

export interface TradeAsset {
  asset_type: "player" | "pick"
  player_id?: string | null
  player_name?: string | null
  player_position?: string | null
  pick_owner_roster_id?: number | null
  pick_owner_name?: string | null
  pick_year?: number | null
  pick_round?: number | null
  projected_slot?: string | null
}

export interface ThirdPartyTrade {
  roster_id: number
  sends: TradeAsset[]
  receives: TradeAsset[]
}

export interface DimensionScore {
  score: number
  confidence: "HIGH" | "MEDIUM" | "LOW"
  reasoning: string
}

export interface StrategicDistinction {
  verdict: "advancing" | "negative" | "neutral"
  headline: string
  explanation: string
}

export interface RerouteResult {
  reroute_type: "better_target" | "better_package" | "picks_buyer"
  headline: string
  reasoning: string
  suggested_assets?: TradeAsset[] | null
}

export interface PackageOffer {
  label: string
  send_assets: TradeAsset[]
  receive_assets: TradeAsset[]
  reasoning: string
}

export interface PackageBuilderResult {
  aggressive_open: PackageOffer
  fair_close: PackageOffer
}

export type RecommendationTypeLabel =
  | "trade"
  | "start"
  | "drop"
  | "hold"
  | "shop"
  | "package"
  | "taxi"
  | "reroll"
  | "bid"
  | "stash"
  | "direction"

export type GapClassification =
  | "buy_low"
  | "sell_high"
  | "hold_despite_weak_market"
  | "ignore_false_discount"
  | "market_right_model_cautious"
  | "league_specific_opportunity"

export type HorizonLabel = "immediate" | "this_week" | "30_days" | "offseason" | "next_season"

export type ConfidenceLabel = "HIGH" | "MEDIUM" | "LOW"

export interface SupportingFactor {
  factor_name: string
  direction: "positive" | "negative" | "neutral"
  magnitude: "high" | "medium" | "low"
  explanation: string
}

export interface ModelVsMarketGap {
  market_rank: number | null
  model_rank: number | null
  market_value: number | null
  model_value: number | null
  gap_magnitude: number | null
  gap_direction: "model_above" | "model_below" | "aligned" | null
  gap_classification: GapClassification | null
  explanation: string | null
}

export interface RecommendationCard {
  recommendation_type: RecommendationTypeLabel
  priority_rank: number
  headline: string
  action: string
  target_entity_type: "player" | "pick" | "position" | "manager"
  target_entity_ids: string[]
  why_summary: string
  supporting_factors: SupportingFactor[]
  confidence_label: ConfidenceLabel
  confidence_score: number
  downside_of_inaction: string
  what_would_change_this_call: string
  horizon: HorizonLabel
  league_specificity_notes: string | null
  manager_specificity_notes: string | null
  model_vs_market_gap: ModelVsMarketGap | null
  cta_label: string
  cta_destination: string
}

export interface TradeEvaluation {
  market_fairness: DimensionScore
  roster_fit: DimensionScore
  direction_fit: DimensionScore
  timing_quality: DimensionScore
  insulation_delta: DimensionScore
  liquidity_delta: DimensionScore
  manager_exploit_quality: DimensionScore
  strategic_distinction: StrategicDistinction
  reroutes?: RerouteResult[] | null
  package?: PackageBuilderResult | null
  recommendation_context?: RecommendationContext | null
  recommendation_cards?: RecommendationCard[] | null
}

export interface PlayerSearchResult {
  player_id: string
  full_name: string
  position: string
  team?: string | null
  roster_id: number
  roster_name: string
}

export interface PickSearchResult {
  original_owner_id: number
  current_owner_id: number
  original_owner_name: string
  pick_year: number
  round: number
  projected_slot: string
  current_owner_name: string
}

export interface TradeRosterResult {
  roster_id: number
  roster_name: string
}

export type TimingLabel =
  | "sell_now"
  | "hold_until_rookie_fever"
  | "use_on_the_clock"

export interface PickValue {
  pick: {
    asset_type: "pick"
    pick_owner_roster_id: number
    pick_year: number
    pick_round: number
    projected_slot?: string | null
  }
  base_value: number
  timed_value: number
  league_adjusted_value: number
  demand_adjusted_value: number
  expected_draft_slot: number
  timing_label: TimingLabel
  timing_reasoning: string
  class_strength_signal: number
  years_out: number
  computed_at: string
  rule_citation: string | null
}

export interface RuleScanEntry {
  rule: string
  support_level: "supported" | "partially_supported" | "unsupported"
  reason: string
  distorts_recommendations: boolean
}

export interface LeagueFormatScan {
  league_id: string
  entries: RuleScanEntry[]
  needs_acknowledgment: boolean
  league_unsupported: boolean
}

export interface FormatAcknowledgment {
  league_id: string
  acknowledged_rules: string[]
  acknowledged_at: string
}

export interface AcknowledgedResponse {
  league_id: string
  acknowledged: boolean
  acknowledgment: FormatAcknowledgment | null
}

export interface LeagueDraftOrderRule {
  non_playoff_basis: "inverse_standings" | "max_points_for"
  playoff_ordering: "by_finish" | "by_record" | "by_points_for"
  tiebreaker: "points_against" | "points_for" | "commissioner"
}

export interface DraftOrderRuleResponse {
  league_id: string
  rule: LeagueDraftOrderRule
}

export interface RookiePlayer {
  player_id: string
  full_name: string
  position: string
  archetype_label: string
  risk_band: "Low" | "Moderate" | "High"
  composite_score: number
  tier_number: number
  available_probability_by_slot: Record<string, number>
}

export interface SubFlag {
  signal_name: string
  direction: "positive" | "negative" | "neutral"
  magnitude_str: string
}

export interface HistoricalComp {
  player_id: string
  player_name: string
  role: "ceiling" | "median" | "floor"
  outcome_bucket: "hit" | "mediocre" | "bust"
  match_reason: string
}

export interface ProspectModelOutput {
  league_id: string
  draft_season: number
  player_id: string
  player_name: string
  position: string
  archetype_label: string
  hit_rate_bucket: "High hit rate" | "Moderate hit rate" | "Low hit rate"
  tier: number
  predicted_tier: number
  predicted_bucket: "hit" | "mediocre" | "bust"
  risk_band: string
  comps: HistoricalComp[]
  overvalue_flag_direction: "overvalued" | "undervalued" | null
  overvalue_magnitude: number | null
  low_confidence: boolean
  sub_flags: SubFlag[]
  computed_at: string
}

export interface RookieTier {
  tier_number: number
  label: string
  players: RookiePlayer[]
}

export interface RookieBoardResponse {
  league_id: string
  league_format: string
  class_strength_signal: number
  tiers: RookieTier[]
  computed_at: string
  recommendation_cards?: RecommendationCard[] | null
}

export interface RookieBoardWithContext {
  rookie_board: RookieBoardResponse
  recommendation_context: RecommendationContext
}

export interface TradeVerdict {
  verdict: "trade" | "use"
  label: string
  reasoning: string
}

export interface TendencyWarning {
  warning_type: "positional_run" | "value_gap" | "manager_tendency"
  title: string
  description: string
  affected_players?: string[]
}

export interface DraftRoomResponse {
  league_id: string
  pick_slot: number
  pick_slot_display: string
  trade_verdict: TradeVerdict
  best_in_abstract: RookiePlayer | null
  tendency_warnings: TendencyWarning[]
  recommendation_cards?: RecommendationCard[] | null
}

export interface ExposureRow {
  player_id: string
  full_name: string
  position: string
  team: string | null
  owned_in_leagues: string[]
  league_count: number
  hedge_rec: string | null
}

export interface CorrelatedRiskPlayer {
  player_id: string
  full_name: string
  league_id: string
}

export interface CorrelatedRiskRow {
  nfl_team: string
  players: CorrelatedRiskPlayer[]
  league_ids: string[]
  risk_string: string
}

export interface PortfolioExposureResponse {
  exposure: ExposureRow[]
  correlated_risk: CorrelatedRiskRow[]
}

export interface RecalibrationHealth {
  last_recalibrated_at: string | null
}

export interface SnapshotAnchor {
  snapshot_id: number
  snapshot_at: string
  anchor_type: "trade" | "roster_change" | "season_start" | "season_end"
  label: string
}

export type CalendarState =
  | "startup"
  | "preseason"
  | "early_season"
  | "trade_deadline"
  | "playoffs"
  | "rookie_fever"
  | "post_combine"
  | "post_nfl_draft"

export interface FreshnessTag {
  domain: string
  last_updated: string | null
  is_stale: boolean
  warning: string | null
}

export interface CalendarContext {
  active_state: CalendarState
  detected_at: string
}

export interface RecommendationContext {
  calendar_state: CalendarState
  freshness_tags: FreshnessTag[]
  calendar_note: string | null
}

export interface PickListResponse {
  picks: PickValue[]
  recommendation_context: RecommendationContext
}

export interface DiffRow {
  field: string
  field_type:
    | "direction_label"
    | "scorecard"
    | "player_value"
    | "pick_capital"
    | "departed"
    | "added"
  delta: number | null
  old_value: string | null
  new_value: string | null
  display_string: string
}

export interface LineupSlotScore {
  position: string
  player_id: string
  player_name: string
  starter_value: number
  replacement_level: number
  score: number
  contender_benchmark: number
  playoff_target: number
  title_target: number
  elite_target: number
  upgrade_leverage_score: number
  gap_to_playoff_target: number
  gap_to_title_target: number
  gap_to_elite_target: number
  weak_by_median: boolean
  below_playoff_target: boolean
  below_title_target: boolean
  below_elite_target: boolean
  weak_relative_to_contender: boolean
  benchmark_used: boolean
  benchmark_source: string
  benchmark_sample_size: number
  elite_insulation_guard: boolean
  format_urgency_weight: number
  player_context_flags: string[]
}

export interface LineupResult {
  league_id: string
  roster_id: number
  computed_at: string | null
  slot_scores: LineupSlotScore[]
  total_lineup_score: number
  overall_playoff_target: number
  overall_title_target: number
  overall_elite_target: number
  overall_gap_to_playoff_target: number
  overall_gap_to_title_target: number
  overall_gap_to_elite_target: number
  overall_benchmark_source: string
  overall_benchmark_sample_size: number
  title_window_label: "Peak Window" | "Fading Window" | "Outside Window"
  title_window_composite: number
  ceiling_score: number
  stability_score: number
  depth_score: number
  recommendation_cards?: RecommendationCard[] | null
  contender_benchmark_used: boolean
  upgrade_leverage_point: string
  upgrade_title_equity_delta: number
}

export interface HygieneSuggestion {
  action_type:
    | "consolidate"
    | "cut"
    | "stash"
    | "taxi"
    | "hold"
    | "shop"
    | "package"
    | "handcuff_speculative"
    | "reroll_into_pick"
    | "throw_in_now"
  primary_player_ids: string[]
  primary_player_names: string[]
  target_player_id: string | null
  target_player_name: string | null
  counterparty_roster_id: number | null
  counterparty_name: string | null
  reasoning: string
  direction_fit_score: number
  timing_rationale: string
  packaging_rationale: string | null
  player_context_flags: string[]
}

export interface HygieneResult {
  league_id: string
  roster_id: number
  computed_at: string | null
  suggestions: HygieneSuggestion[]
  recommendation_cards?: RecommendationCard[] | null
}

export interface LeagueTaxiConfig {
  taxi_slots: number
  taxi_years_eligible: number
  years_pro_cutoff: number
  manual_exceptions: string[]
}

export interface TaxiConfigResponse {
  league_id: string
  config: LeagueTaxiConfig | null
}

export interface SlotOccupancy {
  taxi_used: number
  taxi_total: number
  ir_used: number
  ir_total: number
}

export interface WaiverRecommendation {
  player_id: string
  player_name: string
  position: string
  team: string | null
  recommendation_label: "faab_bid" | "rolling_waiver" | "free_agent_only"
  bid_low: number | null
  bid_mid: number | null
  bid_high: number | null
  urgency: "High" | "Medium" | "Low"
  rationale: string
  is_immediate_start: boolean
  data_freshness_warning: boolean
  hours_since_ingest: number | null
}

export interface WaiverRecommendationsResponse {
  league_id: string
  roster_id: number
  waiver_type_label: string
  waiver_type_raw: number
  remaining_faab: number | null
  total_faab: number | null
  recommendations: WaiverRecommendation[]
  recommendation_cards?: RecommendationCard[] | null
  data_freshness_warning: boolean
  computed_at: string
}

export interface StartupPickValuation {
  pick_slot: string
  pick_slot_number: number
  projected_player_name: string | null
  projected_player_id?: string | null
  tier_label: string
  trade_up_recommended: boolean
  trade_down_recommended: boolean
  trade_reasoning: string | null
  pick_value: number
}

export interface StartupContext {
  league_id: string
  draft_status: "pre_draft" | "drafting" | "complete" | "unknown"
  startup_mode_available: boolean
  build_template: "win_now" | "balanced" | "rebuild"
  direction_label: string
  build_template_hint: string
  pick_valuations: StartupPickValuation[]
  computed_at: string
}

export interface OrphanIntakeDimension {
  score: number
  label: string
  summary: string
}

export interface OrphanIntake {
  league_id: string
  roster_id: number
  composite_score: number
  composite_label: "Distressed" | "Rebuilder" | "Balanced" | "Ready to Compete"
  age_curve: OrphanIntakeDimension
  pick_capital: OrphanIntakeDimension
  dead_spots: OrphanIntakeDimension
  lineup_viability: OrphanIntakeDimension
  liquidation_options: OrphanIntakeDimension
  computed_at: string
}

export interface ActionPlanItem {
  priority_rank: number
  category: "add" | "drop" | "trade" | "hold" | "evaluate"
  headline: string
  rationale: string
  urgency: "this_week" | "30_days" | "offseason"
  target_entity_type: "player" | "pick" | "position" | "manager"
  target_entity_ids: string[]
  confidence_label: "HIGH" | "MEDIUM" | "LOW"
}

export interface ActionPlan {
  league_id: string
  roster_id: number
  generated_at: string
  plan_type: "orphan_intake" | "startup" | "new_connection"
  items: ActionPlanItem[]
  recommendation_cards?: RecommendationCard[] | null
  summary: string
}

export type TrendLabel = "will_rise" | "will_maintain" | "will_fall"
export type TrendConfidence = "HIGH" | "MEDIUM" | "LOW"
export type SuggestedAction = "buy" | "sell" | "hold"

export interface SimilarPlayer {
  player_id: string
  player_name: string
  similarity_score: number
  archetype_label: string | null
  context: string
}

export interface OpportunityFeedItem {
  player_id: string
  player_name: string
  position: string
  trend_label: TrendLabel
  trend_confidence: TrendConfidence
  adp_gap: number
  suggested_action: SuggestedAction
  impact_score: number
  why_summary: string
  owned_in_leagues: string[]
  similar_players: SimilarPlayer[]
  conflict_explanation: string | null
  calendar_escalated: boolean
  calendar_escalation_label: string | null
}

export interface OpportunityFeedResponse {
  items: OpportunityFeedItem[]
  total: number
  computed_at: string
}
