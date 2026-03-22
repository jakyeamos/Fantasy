import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"

import { dashboardSummaryOptions } from "@/api/queries"
import { LeagueCard } from "@/components/LeagueCard"
import { SnapshotStatus } from "@/components/SnapshotStatus"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

export const Route = createFileRoute("/")({
  component: DashboardPage,
})

function DashboardSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 lg:gap-6">
      {Array.from({ length: 3 }).map((_, index) => (
        <Card key={index} className="min-h-[180px]">
          <CardHeader className="space-y-3">
            <Skeleton className="h-4 w-28" />
            <Skeleton className="h-7 w-40" />
          </CardHeader>
          <CardContent className="space-y-3">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-3 w-28" />
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

function DashboardPage() {
  const query = useQuery(dashboardSummaryOptions)

  if (query.isLoading) {
    return <DashboardSkeleton />
  }

  if (query.isError) {
    return (
      <p className="text-sm text-muted-foreground">
        Dashboard data unavailable. Check that the backend is running, then refresh.
      </p>
    )
  }

  if (!query.data || query.data.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No leagues connected. Add a league ID to get started.
      </p>
    )
  }

  const lastSnapshotAt = query.data
    .map((league) => league.last_snapshot_at)
    .filter(Boolean)
    .sort()
    .at(-1) ?? null

  return (
    <div className="space-y-8">
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 lg:gap-6">
        {query.data.map((league) => (
          <LeagueCard key={league.league_id} {...league} />
        ))}
      </section>

      <SnapshotStatus lastSnapshotAt={lastSnapshotAt} />

      <Card className="border-dashed">
        <CardHeader>
          <CardTitle>Cross-League Exposure Alerts</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Cross-league exposure alerts will appear here once the portfolio layer is implemented.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
