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
