import { useState } from "react"

import { useQuery } from "@tanstack/react-query"
import { Link, Outlet, createFileRoute } from "@tanstack/react-router"

import { leagueDetailOptions } from "@/api/queries"
import { ConcentrationAlertBanner } from "@/components/ConcentrationAlertBanner"
import { ExploitWindowPanel } from "@/components/ExploitWindowPanel"
import { RisersFallersList } from "@/components/RisersFallersList"
import { SnapshotStatus } from "@/components/SnapshotStatus"
import { SnapshotComparisonSheet } from "@/components/SnapshotComparisonSheet"
import { LeaguePickList } from "@/components/picks/LeaguePickList"
import { Badge } from "@/components/ui/badge"
import { Button, buttonClasses } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { formatModelLabel } from "@/lib/utils"

export const Route = createFileRoute("/league/$leagueId")({
  component: LeagueDetailPage,
})

function badgeVariant(confidence: "High" | "Medium" | "Low" | "--") {
  if (confidence === "High") return "default"
  if (confidence === "Medium") return "secondary"
  return "outline"
}

function LeagueDetailPage() {
  const { leagueId } = Route.useParams()
  const query = useQuery(leagueDetailOptions(leagueId))
  const [comparisonOpen, setComparisonOpen] = useState(false)

  if (query.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-72" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  if (query.isError || !query.data) {
    return (
      <p className="text-sm text-muted-foreground">
        League data unavailable. Try refreshing or check the backend connection.
      </p>
    )
  }

  const league = query.data

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-3">
              <CardTitle className="text-lg">{league.league_name}</CardTitle>
              <Badge variant={badgeVariant(league.confidence_band)}>
                {league.confidence_band}
              </Badge>
            </div>
            <div>
              <p className="text-xl font-semibold">
                {formatModelLabel(league.direction_label)}
              </p>
              <p className="mt-3 text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                Roster note
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                {league.primary_weakness}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Link
              to="/league/$leagueId/managers"
              params={{ leagueId }}
              className={buttonClasses({ variant: "outline" })}
            >
              View Managers
            </Link>
            <Link
              to="/league/$leagueId/rookie-board"
              params={{ leagueId }}
              className={buttonClasses({ variant: "outline" })}
            >
              Rookie Board
            </Link>
            <Link
              to="/draft-room"
              search={{ leagueId, pickSlot: 1 }}
              className={buttonClasses({ variant: "outline" })}
            >
              Enter Draft Room
            </Link>
            <Link
              to="/trades"
              search={{ leagueId }}
              className={buttonClasses({})}
            >
              Evaluate Trade
            </Link>
          </div>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center justify-between gap-3">
          <SnapshotStatus lastSnapshotAt={league.last_snapshot_at} />
          {league.user_roster_id ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setComparisonOpen(true)}
            >
              Compare to snapshot
            </Button>
          ) : null}
        </CardContent>
      </Card>

      <ConcentrationAlertBanner
        leagueId={leagueId}
        userRosterPlayerIds={league.user_roster_player_ids}
      />
      <RisersFallersList risers={league.risers} fallers={league.fallers} />
      <LeaguePickList leagueId={leagueId} rosterId={league.user_roster_id} />
      <ExploitWindowPanel leagueId={leagueId} windows={league.exploit_windows} />
      {league.user_roster_id ? (
        <SnapshotComparisonSheet
          leagueId={leagueId}
          rosterId={league.user_roster_id}
          open={comparisonOpen}
          onOpenChange={setComparisonOpen}
        />
      ) : null}
      <Outlet />
    </div>
  )
}
