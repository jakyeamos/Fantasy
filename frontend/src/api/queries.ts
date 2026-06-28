import { queryOptions } from "@tanstack/react-query"

import type {
  ActionPlan,
  AcknowledgedResponse,
  CalendarContext,
  CommandCenterResponse,
  FreshnessTag,
  CorrelatedRiskRow,
  DashboardLeagueSummary,
  DiffRow,
  DraftOrderRuleResponse,
  DraftRoomResponse,
  ExposureRow,
  HygieneResult,
  LeagueDetailResponse,
  LeagueDraftOrderRule,
  LeagueFormatScan,
  LeagueRosterOption,
  LeagueTaxiConfig,
  LineupResult,
  ManagerProfile,
  ManagerSummary,
  OrphanIntake,
  OpportunityFeedResponse,
  PickSearchResult,
  PickValue,
  PortfolioExposureResponse,
  ProspectModelOutput,
  PickListResponse,
  PlayerRankingsResponse,
  RecalibrationHealth,
  RookieBoardResponse,
  RookieBoardWithContext,
  SnapshotAnchor,
  SnapshotStatus,
  SlotOccupancy,
  StartupContext,
  TaxiConfigResponse,
  WaiverRecommendationsResponse,
  WeeklyContextRefreshResponse,
  WeeklyEdgeResponse,
} from "@/api/types"

export async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, init)
  if (!response.ok) {
    throw new Error(`Request failed: ${path}`)
  }
  return (await response.json()) as T
}

export async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    throw new Error(`Request failed: ${path}`)
  }
  return (await response.json()) as T
}

export async function deleteJson<T>(path: string): Promise<T> {
  const response = await fetch(`/api${path}`, { method: "DELETE" })
  if (!response.ok) {
    throw new Error(`Request failed: ${path}`)
  }
  return (await response.json()) as T
}

export const dashboardSummaryOptions = queryOptions({
  queryKey: ["dashboard", "summary"],
  queryFn: () => getJson<DashboardLeagueSummary[]>("/dashboard/summary"),
  staleTime: 5 * 60 * 1000,
})

export const commandCenterOptions = queryOptions({
  queryKey: ["actions", "command-center"],
  queryFn: () => getJson<CommandCenterResponse>("/actions/command-center"),
  staleTime: 60 * 1000,
})

export const leagueActionsOptions = (leagueId: string) =>
  queryOptions({
    queryKey: ["actions", "league", leagueId],
    queryFn: () => getJson<CommandCenterResponse>(`/actions/league/${leagueId}`),
    staleTime: 60 * 1000,
    enabled: leagueId.trim().length > 0,
  })

export async function recomputeActions(): Promise<CommandCenterResponse> {
  return postJson<CommandCenterResponse>("/actions/recompute", {})
}

export const leagueDetailOptions = (leagueId: string, rosterId?: number | null) =>
  queryOptions({
    queryKey: ["dashboard", "league", leagueId, rosterId ?? "default"],
    queryFn: () => {
      const params = new URLSearchParams()
      if (rosterId && rosterId > 0) {
        params.set("roster_id", String(rosterId))
      }
      const suffix = params.size ? `?${params.toString()}` : ""
      return getJson<LeagueDetailResponse>(`/dashboard/league/${leagueId}${suffix}`)
    },
    staleTime: 5 * 60 * 1000,
  })

export const leagueRosterOptions = (leagueId: string) =>
  queryOptions({
    queryKey: ["dashboard", "league", leagueId, "rosters"],
    queryFn: () => getJson<LeagueRosterOption[]>(`/dashboard/league/${leagueId}/rosters`),
    staleTime: 5 * 60 * 1000,
    enabled: leagueId.trim().length > 0,
  })

export const playerRankingsOptions = (leagueId: string, rosterId?: number | null) =>
  queryOptions({
    queryKey: ["dashboard", "league", leagueId, "player-rankings", rosterId ?? "default"],
    queryFn: () => {
      const params = new URLSearchParams()
      if (rosterId && rosterId > 0) {
        params.set("roster_id", String(rosterId))
      }
      const suffix = params.size ? `?${params.toString()}` : ""
      return getJson<PlayerRankingsResponse>(
        `/dashboard/league/${leagueId}/player-rankings${suffix}`,
      )
    },
    staleTime: 5 * 60 * 1000,
    enabled: leagueId.trim().length > 0,
  })

export const snapshotStatusOptions = queryOptions({
  queryKey: ["snapshots", "status"],
  queryFn: () => getJson<SnapshotStatus[]>("/snapshots/status"),
  staleTime: 30 * 1000,
})

export const managerSummariesOptions = (leagueId: string) =>
  queryOptions({
    queryKey: ["profiling", "managers", leagueId],
    queryFn: () =>
      getJson<ManagerSummary[]>(`/profiling/leagues/${leagueId}/managers`),
    staleTime: 60_000,
  })

export const managerProfileOptions = (leagueId: string, managerId: string) =>
  queryOptions({
    queryKey: ["profiling", "manager", leagueId, managerId],
    queryFn: () =>
      getJson<ManagerProfile>(
        `/profiling/leagues/${leagueId}/managers/${managerId}`,
      ),
    staleTime: 60_000,
  })

export const pickValuesOptions = (
  leagueId: string,
  options?: {
    targetManagerId?: number | null
    currentOwnerRosterId?: number | null
  },
) =>
  queryOptions({
    queryKey: [
      "picks",
      leagueId,
      options?.targetManagerId ?? "neutral",
      options?.currentOwnerRosterId ?? "all",
    ],
    queryFn: () => {
      const params = new URLSearchParams()
      if (options?.targetManagerId) {
        params.set("target_manager_id", String(options.targetManagerId))
      }
      if (options?.currentOwnerRosterId) {
        params.set("current_owner_roster_id", String(options.currentOwnerRosterId))
      }
      const suffix = params.size ? `?${params.toString()}` : ""
      return getJson<PickListResponse>(`/picks/${leagueId}${suffix}`).then(
        (response) => response.picks,
      )
    },
    staleTime: 5 * 60 * 1000,
    enabled: leagueId.trim().length > 0,
  })

export const pickListOptions = (leagueId: string, rosterId?: number | null) =>
  queryOptions({
    queryKey: ["picks", "list", leagueId, rosterId ?? "all"],
    queryFn: () => {
      const params = new URLSearchParams()
      if (rosterId) {
        params.set("current_owner_roster_id", String(rosterId))
      }
      const suffix = params.size ? `?${params.toString()}` : ""
      return getJson<PickListResponse>(`/picks/${leagueId}${suffix}`)
    },
    staleTime: 5 * 60 * 1000,
    enabled: leagueId.trim().length > 0,
  })

export const draftOrderRuleOptions = (leagueId: string) =>
  queryOptions({
    queryKey: ["picks", leagueId, "draft-order-rule"],
    queryFn: () => getJson<DraftOrderRuleResponse | null>(`/picks/${leagueId}/draft-order-rule`),
    staleTime: 5 * 60 * 1000,
    enabled: leagueId.trim().length > 0,
  })

export async function saveDraftOrderRule(
  leagueId: string,
  rule: LeagueDraftOrderRule,
): Promise<DraftOrderRuleResponse> {
  const response = await fetch(`/api/picks/${leagueId}/draft-order-rule`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(rule),
  })
  if (!response.ok) {
    throw new Error("Failed to save draft order rule")
  }
  return (await response.json()) as DraftOrderRuleResponse
}

export const pickInventoryOptions = (
  leagueId: string,
  rosterId?: number | null,
) =>
  queryOptions({
    queryKey: ["trade", "picks", "inventory", leagueId, rosterId ?? "all"],
    queryFn: () => {
      const params = new URLSearchParams({ league_id: leagueId })
      if (rosterId) {
        params.set("roster_id", String(rosterId))
      }
      return getJson<PickSearchResult[]>(`/trade/picks/search?${params.toString()}`)
    },
    staleTime: 60_000,
    enabled: leagueId.trim().length > 0,
  })

export const rookieBoardOptions = (leagueId: string) =>
  queryOptions({
    queryKey: ["rookie-board", leagueId],
    queryFn: () => getJson<RookieBoardWithContext>(`/rookie-board/${leagueId}`),
    staleTime: 15 * 60 * 1000,
    enabled: leagueId.trim().length > 0,
  })

export const draftRoomOptions = (leagueId: string, pickSlot: number) =>
  queryOptions({
    queryKey: ["draft-room", leagueId, pickSlot],
    queryFn: () => getJson<DraftRoomResponse>(`/draft-room/${leagueId}/${pickSlot}`),
    staleTime: 15 * 60 * 1000,
    enabled: leagueId.trim().length > 0 && pickSlot > 0,
  })

export const prospectModelOutputsOptions = (leagueId: string) =>
  queryOptions({
    queryKey: ["prospects", "model-outputs", leagueId],
    queryFn: () => getJson<ProspectModelOutput[]>(`/prospects/model-outputs/${leagueId}`),
    staleTime: 30 * 60 * 1000,
    enabled: leagueId.trim().length > 0,
  })

export const portfolioExposureOptions = (ownerId?: string | null) =>
  queryOptions({
    queryKey: ["portfolio", "exposure", ownerId ?? "default"],
    queryFn: () => {
      const params = new URLSearchParams()
      if (ownerId) {
        params.set("owner_id", ownerId)
      }
      const suffix = params.size ? `?${params.toString()}` : ""
      return getJson<PortfolioExposureResponse>(`/portfolio/exposure${suffix}`)
    },
    staleTime: 5 * 60 * 1000,
  })

export const opportunityFeedOptions = queryOptions({
  queryKey: ["opportunities", "feed"],
  queryFn: async () => {
    const controller = new AbortController()
    const timeoutId = window.setTimeout(() => controller.abort(), 10_000)
    try {
      return await getJson<OpportunityFeedResponse>("/opportunities", {
        signal: controller.signal,
      })
    } catch (error) {
      if (controller.signal.aborted) {
        const timeoutError = new Error(
          "Opportunity feed request timed out after 10 seconds.",
        )
        timeoutError.name = "TimeoutError"
        throw timeoutError
      }
      throw error
    } finally {
      window.clearTimeout(timeoutId)
    }
  },
  retry: false,
  staleTime: 5 * 60 * 1000,
})

export const portfolioHealthOptions = () =>
  queryOptions({
    queryKey: ["portfolio", "health"],
    queryFn: () => getJson<RecalibrationHealth>("/portfolio/health"),
    staleTime: 60 * 60 * 1000,
  })

export const snapshotAnchorsOptions = (leagueId: string) =>
  queryOptions({
    queryKey: ["snapshot-anchors", leagueId],
    queryFn: () => getJson<SnapshotAnchor[]>(`/leagues/${leagueId}/snapshot-anchors`),
    staleTime: 60 * 1000,
    enabled: leagueId.trim().length > 0,
  })

export const calendarContextOptions = (leagueId: string) =>
  queryOptions({
    queryKey: ["context", "calendar", leagueId],
    queryFn: () => getJson<CalendarContext>(`/context/${leagueId}/calendar`),
    staleTime: 60 * 1000,
    enabled: leagueId.trim().length > 0,
  })

export const freshnessOptions = (leagueId: string) =>
  queryOptions({
    queryKey: ["context", "freshness", leagueId],
    queryFn: () => getJson<FreshnessTag[]>(`/context/${leagueId}/freshness`),
    staleTime: 60 * 1000,
    enabled: leagueId.trim().length > 0,
  })

export const snapshotDiffOptions = (
  leagueId: string,
  snapshotId: number,
  rosterId: number,
) =>
  queryOptions({
    queryKey: ["snapshot-diff", leagueId, snapshotId, rosterId],
    queryFn: () =>
      getJson<DiffRow[]>(
        `/leagues/${leagueId}/snapshot-diff?snapshot_id=${snapshotId}&roster_id=${rosterId}`,
      ),
    staleTime: 5 * 60 * 1000,
    enabled: leagueId.trim().length > 0 && snapshotId > 0 && rosterId > 0,
  })

export const lineupScoreOptions = (leagueId: string, rosterId: number) =>
  queryOptions({
    queryKey: ["intelligence", "lineup", leagueId, rosterId],
    queryFn: () => getJson<LineupResult>(`/intelligence/lineup/${leagueId}/${rosterId}`),
    staleTime: 5 * 60 * 1000,
    enabled: leagueId.trim().length > 0 && rosterId > 0,
  })

export const hygieneOptions = (leagueId: string, rosterId: number) =>
  queryOptions({
    queryKey: ["intelligence", "hygiene", leagueId, rosterId],
    queryFn: () => getJson<HygieneResult>(`/intelligence/hygiene/${leagueId}/${rosterId}`),
    staleTime: 5 * 60 * 1000,
    enabled: leagueId.trim().length > 0 && rosterId > 0,
  })

export const taxiConfigOptions = (leagueId: string) =>
  queryOptions({
    queryKey: ["leagues", leagueId, "taxi-config"],
    queryFn: () => getJson<TaxiConfigResponse>(`/leagues/${leagueId}/taxi-config`),
    staleTime: 5 * 60 * 1000,
    enabled: leagueId.trim().length > 0,
  })

export const slotOccupancyOptions = (leagueId: string, rosterId: number) =>
  queryOptions({
    queryKey: ["leagues", leagueId, "slot-occupancy", rosterId],
    queryFn: () => getJson<SlotOccupancy>(`/leagues/${leagueId}/slot-occupancy/${rosterId}`),
    staleTime: 5 * 60 * 1000,
    enabled: leagueId.trim().length > 0 && rosterId > 0,
  })

export async function saveTaxiConfig(
  leagueId: string,
  config: LeagueTaxiConfig,
): Promise<TaxiConfigResponse> {
  const res = await fetch(`/api/leagues/${leagueId}/taxi-config`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  })
  if (!res.ok) throw new Error("Failed to save taxi config")
  return (await res.json()) as TaxiConfigResponse
}

export const leagueFormatScanOptions = (leagueId: string) =>
  queryOptions({
    queryKey: ["trust", leagueId, "scan"],
    queryFn: () => getJson<LeagueFormatScan>(`/trust/${leagueId}/scan`),
    staleTime: 5 * 60 * 1000,
    enabled: leagueId.trim().length > 0,
  })

export const leagueAcknowledgedOptions = (leagueId: string) =>
  queryOptions({
    queryKey: ["trust", leagueId, "acknowledged"],
    queryFn: () => getJson<AcknowledgedResponse>(`/trust/${leagueId}/acknowledged`),
    staleTime: 0,
    enabled: leagueId.trim().length > 0,
  })

export async function acknowledgeLeagueFormat(leagueId: string): Promise<void> {
  const res = await fetch(`/api/trust/${leagueId}/acknowledge`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  })
  if (!res.ok) throw new Error("Failed to acknowledge league format")
}

export function waiverRecommendationsOptions(leagueId: string, rosterId: number) {
  return queryOptions({
    queryKey: ["waiver-recommendations", leagueId, rosterId],
    queryFn: () =>
      getJson<WaiverRecommendationsResponse>(`/waiver/${leagueId}/${rosterId}/recommendations`),
    staleTime: 60 * 1000,
    enabled: leagueId.trim().length > 0 && rosterId > 0,
  })
}

export function weeklyEdgeOptions(leagueId: string, rosterId: number) {
  return queryOptions({
    queryKey: ["weekly", "edge", leagueId, rosterId],
    queryFn: () => getJson<WeeklyEdgeResponse>(`/weekly/league/${leagueId}/${rosterId}/edge`),
    staleTime: 60 * 1000,
    enabled: leagueId.trim().length > 0 && rosterId > 0,
  })
}

export function refreshWeeklyContext(
  leagueId: string,
  season?: number | null,
): Promise<WeeklyContextRefreshResponse> {
  const params = new URLSearchParams()
  if (season) {
    params.set("season", String(season))
  }
  const suffix = params.size ? `?${params.toString()}` : ""
  return postJson<WeeklyContextRefreshResponse>(
    `/weekly/league/${leagueId}/refresh-context${suffix}`,
    {},
  )
}

export async function runOrphanIntake(
  leagueId: string,
  rosterId: number,
): Promise<OrphanIntake> {
  return postJson<OrphanIntake>(`/waiver/${leagueId}/${rosterId}/orphan-intake`, {})
}

export function actionPlanOptions(leagueId: string, rosterId: number) {
  return queryOptions({
    queryKey: ["action-plan", leagueId, rosterId],
    queryFn: () => getJson<ActionPlan>(`/waiver/${leagueId}/${rosterId}/action-plan`),
    staleTime: 60 * 1000,
    enabled: leagueId.trim().length > 0 && rosterId > 0,
  })
}

export function startupContextOptions(leagueId: string, rosterId: number = 0) {
  return queryOptions({
    queryKey: ["startup-context", leagueId, rosterId],
    queryFn: () => getJson<StartupContext>(`/startup/${leagueId}/context?roster_id=${rosterId}`),
    staleTime: 60 * 1000,
    enabled: leagueId.trim().length > 0,
  })
}
