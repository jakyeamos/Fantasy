import type { OpportunityFeedItem } from "@/api/types"

export type OpportunityScopeFilter = "all" | OpportunityFeedItem["availability"]
export type OpportunityActionFilter =
  | "all"
  | OpportunityFeedItem["suggested_action"]

export interface OpportunityFilterState {
  scopeFilter: OpportunityScopeFilter
  actionFilter: OpportunityActionFilter
  highConfidenceOnly: boolean
  leagueFilter: string
  includeSpeculative: boolean
  lineupFitOnly: boolean
}

export function filterOpportunityItems(
  items: OpportunityFeedItem[],
  filters: OpportunityFilterState,
): OpportunityFeedItem[] {
  return items.filter((item) => {
    if (
      !filters.includeSpeculative &&
      item.trend_confidence === "LOW" &&
      item.availability === "available"
    ) {
      return false
    }
    if (
      filters.scopeFilter !== "all" &&
      item.availability !== filters.scopeFilter
    ) {
      return false
    }
    if (
      filters.actionFilter !== "all" &&
      item.suggested_action !== filters.actionFilter
    ) {
      return false
    }
    if (filters.highConfidenceOnly && item.trend_confidence !== "HIGH") {
      return false
    }
    if (filters.lineupFitOnly && item.weekly_fit === null) {
      return false
    }
    if (filters.leagueFilter !== "all") {
      const leagueIds = new Set([
        ...item.owned_in_leagues,
        item.cta?.league_id ?? "",
      ])
      if (!leagueIds.has(filters.leagueFilter)) {
        return false
      }
    }
    return true
  })
}
