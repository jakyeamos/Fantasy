import { queryOptions } from "@tanstack/react-query"

import type {
  CorrelatedRiskRow,
  DashboardLeagueSummary,
  DiffRow,
  DraftRoomResponse,
  ExposureRow,
  LeagueDetailResponse,
  ManagerProfile,
  ManagerSummary,
  PickSearchResult,
  PickValue,
  PortfolioExposureResponse,
  RecalibrationHealth,
  RookieBoardResponse,
  SnapshotAnchor,
  SnapshotStatus,
} from "@/api/types"

export async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`/api${path}`)
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

export const leagueDetailOptions = (leagueId: string) =>
  queryOptions({
    queryKey: ["dashboard", "league", leagueId],
    queryFn: () => getJson<LeagueDetailResponse>(`/dashboard/league/${leagueId}`),
    staleTime: 5 * 60 * 1000,
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
      return getJson<PickValue[]>(`/picks/${leagueId}${suffix}`)
    },
    staleTime: 5 * 60 * 1000,
    enabled: leagueId.trim().length > 0,
  })

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
    queryFn: () => getJson<RookieBoardResponse>(`/rookie-board/${leagueId}`),
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

export const portfolioExposureOptions = () =>
  queryOptions({
    queryKey: ["portfolio", "exposure"],
    queryFn: () => getJson<PortfolioExposureResponse>("/portfolio/exposure"),
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
