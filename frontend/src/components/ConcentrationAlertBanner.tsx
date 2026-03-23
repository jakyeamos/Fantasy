import { useMemo } from "react"

import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { AlertTriangle } from "lucide-react"

import { portfolioExposureOptions } from "@/api/queries"
import { Badge } from "@/components/ui/badge"
import { buttonClasses } from "@/components/ui/button"

function badgeForCount(count: number) {
  if (count >= 3) {
    return "bg-red-50 text-red-600 dark:bg-red-950/20 dark:text-red-400"
  }
  return "bg-amber-50 text-amber-700 dark:bg-amber-950/20 dark:text-amber-300"
}

export function ConcentrationAlertBanner({
  leagueId,
  userRosterPlayerIds,
}: {
  leagueId: string
  userRosterPlayerIds: string[]
}) {
  const query = useQuery(portfolioExposureOptions())

  const rows = useMemo(() => {
    const playerIds = new Set(userRosterPlayerIds)
    return (query.data?.exposure ?? [])
      .filter((row) => playerIds.has(row.player_id))
      .filter((row) => row.owned_in_leagues.filter((ownedLeagueId) => ownedLeagueId !== leagueId).length > 0)
      .sort((a, b) => b.league_count - a.league_count || a.full_name.localeCompare(b.full_name))
  }, [leagueId, query.data?.exposure, userRosterPlayerIds])

  if (query.isLoading || query.isError || !rows.length) {
    return null
  }

  return (
    <div className="rounded-xl border border-amber-200/70 bg-amber-50/70 p-4 dark:border-amber-950/40 dark:bg-amber-950/20">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 size-4 text-amber-600 dark:text-amber-400" />
        <div className="min-w-0 flex-1 space-y-3">
          <div className="space-y-1">
            <p className="text-sm font-medium text-foreground">Cross-league exposure</p>
            <p className="text-xs text-amber-700 dark:text-amber-300">
              {rows.length} player{rows.length === 1 ? "" : "s"} on this roster are owned in other leagues.
            </p>
          </div>
          <div className="space-y-2">
            {rows.map((row) => (
              <div key={row.player_id} className="flex flex-wrap items-center gap-2 text-sm">
                <span>{row.full_name}</span>
                <Badge variant="outline" className="text-xs">
                  {row.position}
                </Badge>
                <Badge className={badgeForCount(row.league_count)}>
                  {row.league_count} leagues
                </Badge>
                {row.hedge_rec ? (
                  <span className="text-xs text-muted-foreground">{row.hedge_rec}</span>
                ) : null}
              </div>
            ))}
          </div>
          <Link to="/portfolio" className={buttonClasses({ variant: "link", className: "px-0" })}>
            View full exposure →
          </Link>
        </div>
      </div>
    </div>
  )
}
