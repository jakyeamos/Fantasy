export interface DashboardLeagueSummary {
  league_id: string
  league_name: string
  user_roster_id: number | null
  direction_label: string
  confidence_band: "High" | "Medium" | "Low" | "--"
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

export interface LeagueDetailResponse {
  league_id: string
  league_name: string
  user_roster_id: number | null
  user_roster_player_ids: string[]
  direction_label: string
  confidence_band: "High" | "Medium" | "Low" | "--"
  primary_weakness: string
  risers: RiserFallerEntry[]
  fallers: RiserFallerEntry[]
  exploit_windows: ExploitWindowManager[]
  last_snapshot_at: string | null
  last_ingest_at: string | null
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
  reroute_type: "better_target" | "better_package"
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
}

export interface TradeVerdict {
  verdict: "trade" | "use"
  label: string
  reasoning: string
}

export interface TendencyWarning {
  warning_type: "positional_run" | "value_gap"
  title: string
  description: string
}

export interface DraftRoomResponse {
  league_id: string
  pick_slot: number
  pick_slot_display: string
  trade_verdict: TradeVerdict
  best_in_abstract: RookiePlayer | null
  tendency_warnings: TendencyWarning[]
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
