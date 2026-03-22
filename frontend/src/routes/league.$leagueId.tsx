import { useQuery } from "@tanstack/react-query"
import { Link, createFileRoute } from "@tanstack/react-router"

import { leagueDetailOptions } from "@/api/queries"
import { ExploitWindowPanel } from "@/components/ExploitWindowPanel"
import { RisersFallersList } from "@/components/RisersFallersList"
import { SnapshotStatus } from "@/components/SnapshotStatus"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

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
              <p className="text-xl font-semibold">{league.direction_label}</p>
              <p className="mt-2 text-sm text-muted-foreground">
                {league.primary_weakness}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Link to="/league/$leagueId/managers" params={{ leagueId }}>
              <Button variant="outline">View Managers</Button>
            </Link>
            <Link to="/trades" search={{ leagueId }}>
              <Button>Evaluate Trade</Button>
            </Link>
          </div>
        </CardHeader>
        <CardContent>
          <SnapshotStatus lastSnapshotAt={league.last_snapshot_at} />
        </CardContent>
      </Card>

      <RisersFallersList risers={league.risers} fallers={league.fallers} />
      <ExploitWindowPanel leagueId={leagueId} windows={league.exploit_windows} />
    </div>
  )
}
