import { queryOptions } from "@tanstack/react-query"

import type {
  DashboardLeagueSummary,
  LeagueDetailResponse,
  SnapshotStatus,
} from "@/api/types"

async function getJson<T>(path: string): Promise<T> {
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
