import { useMemo } from "react"

import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { AlertTriangle } from "lucide-react"

import { portfolioExposureOptions } from "@/api/queries"
import { Badge } from "@/components/ui/badge"
import { buttonClasses } from "@/components/ui/button"

function badgeForCount(count: number) {
  if (count >= 3) {
    return "border border-destructive/25 bg-destructive/10 text-destructive"
  }
  return "border border-primary/25 bg-primary/10 text-primary"
}

export function ConcentrationAlertBanner({
  leagueId,
  ownerId,
  userRosterPlayerIds,
}: {
  leagueId: string
  ownerId: string | null
  userRosterPlayerIds: string[]
}) {
  const query = useQuery({
    ...portfolioExposureOptions(ownerId),
    enabled: Boolean(ownerId),
  })

  const rows = useMemo(() => {
    const playerIds = new Set(userRosterPlayerIds)
    return (query.data?.exposure ?? [])
      .filter((row) => playerIds.has(row.player_id))
      .filter(
        (row) =>
          row.owned_in_leagues.filter((ownedLeagueId) => ownedLeagueId !== leagueId).length > 0,
      )
      .sort((a, b) => b.league_count - a.league_count || a.full_name.localeCompare(b.full_name))
  }, [leagueId, query.data?.exposure, userRosterPlayerIds])

  if (!ownerId || query.isLoading || query.isError || !rows.length) {
    return null
  }

  return (
    <div className="glass-panel rounded-xl border border-primary/25 bg-card/65 p-5">
      <div className="flex items-start gap-3">
        <div className="flex size-10 items-center justify-center rounded-lg border border-primary/20 bg-primary/10 text-primary">
          <AlertTriangle className="size-4" />
        </div>
        <div className="min-w-0 flex-1 space-y-3">
          <div className="space-y-1">
            <p className="terminal-label text-primary/85">Cross-league exposure</p>
            <p className="text-sm text-muted-foreground">
              {rows.length} player{rows.length === 1 ? "" : "s"} on this roster are owned in other
              leagues.
            </p>
          </div>
          <div className="space-y-2">
            {rows.map((row) => (
              <div
                key={row.player_id}
                className="flex flex-wrap items-center gap-2 rounded-lg border border-border/35 bg-card/45 px-3 py-2 text-sm"
              >
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
          <Link to="/portfolio" className={buttonClasses({ variant: "outline", size: "sm" })}>
            View Full Exposure
          </Link>
        </div>
      </div>
    </div>
  )
}
