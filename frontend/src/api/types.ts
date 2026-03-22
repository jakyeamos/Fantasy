export interface DashboardLeagueSummary {
  league_id: string
  league_name: string
  direction_label: string
  confidence_band: "High" | "Medium" | "Low" | "--"
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
  pick_owner_roster_id?: number | null
  pick_year?: number | null
  pick_round?: number | null
  projected_slot?: string | null
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
  pick_year: number
  round: number
  projected_slot: string
  current_owner_name: string
}
