// Generated from the FastAPI OpenAPI schema. Do not hand edit.
// Run: uv run python -m fantasy.tools.generate_intelligence_types

export type AnalyzeUrlResponse = {
  run_id: string
  url: string
  retrieval: "http" | "browser"
  events?: Array<FootballEvent>
  impacts?: Array<LeagueImpact>
}

export type BriefItem = {
  item_id: string
  event_id: string
  league_id?: string | null
  roster_id?: number | null
  lane: "changed" | "best_move" | "watch"
  priority_rank: number
  headline: string
  why_it_matters: string
  recommended_action?: string | null
  confidence: number
  source_summary: string
  invalidation: string
  impact_summary?: ImpactSummary
  cta_label?: string | null
  cta_destination?: string | null
}

export type EventDetail = {
  event: FootballEvent
  observations?: Array<SourceObservation>
  impacts?: Array<LeagueImpact>
}

export type EventType =
  | "injury_status"
  | "practice_participation"
  | "reserve_transaction"
  | "roster_transaction"
  | "depth_chart_role"
  | "usage_shift"
  | "market_value_change"

export type FootballEvent = {
  event_id: string
  fingerprint: string
  subject_key: string
  event_type: EventType
  player_id?: string | null
  player_name?: string | null
  team?: string | null
  effective_at?: string | null
  observed_at: string
  expires_at?: string | null
  verification_state: VerificationState
  confidence: number
  summary: string
  details?: {}
  observation_ids?: Array<string>
}

export type ImpactSummary = {
  affected_asset_ids?: Array<string>
  before?: {}
  after?: {}
  deltas?: Record<string, number>
}

export type IntelligenceRunResult = {
  run_id: string
  status: "complete" | "degraded" | "failed"
  source_outcomes?: Array<SourceOutcome>
  event_count?: number
  impact_count?: number
  brief_id?: string | null
}

export type LeagueImpact = {
  impact_id: string
  event_id: string
  league_id: string
  roster_id?: number | null
  impact_type: string
  headline: string
  explanation: string
  impact_summary: ImpactSummary
  confidence: number
  actionable?: boolean
  recommended_action?: string | null
  cta_label?: string | null
  cta_destination?: string | null
  invalidation: string
  model_version: string
  computed_at: string
}

export type MorningBrief = {
  brief_id: string
  brief_date: string
  run_id: string
  status: "ready" | "degraded" | "empty"
  created_at: string
  items?: Array<BriefItem>
  source_health?: Array<SourceOutcome>
}

export type ParseStatus = "parsed" | "empty" | "unavailable" | "blocked" | "manual_review"

export type SourceObservation = {
  observation_id: string
  run_id: string
  source_id: string
  source_tier: SourceTier
  url?: string | null
  fetched_at: string
  observed_at?: string | null
  effective_at?: string | null
  coverage_through?: string | null
  content_hash: string
  parse_status: ParseStatus
  evidence_excerpt?: string | null
  payload?: {}
  authoritative?: boolean
  model_extracted?: boolean
}

export type SourceOutcome = {
  source_id: string
  status: "complete" | "partial" | "failed" | "skipped"
  records_seen?: number
  observations_written?: number
  events_written?: number
  fetched_at?: string | null
  coverage_through?: string | null
  message?: string | null
}

export type SourceTier = "structured" | "official" | "public" | "browser"

export type VerificationState = "confirmed" | "watch" | "conflicted" | "expired" | "manual_review"
