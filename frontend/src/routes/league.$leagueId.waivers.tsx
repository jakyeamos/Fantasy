import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"

import { leagueDetailOptions, waiverRecommendationsOptions } from "@/api/queries"
import { WaiverIntelHeader } from "@/components/waivers/WaiverIntelHeader"
import { WaiverPlayerList } from "@/components/waivers/WaiverPlayerList"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

export const Route = createFileRoute("/league/$leagueId/waivers")({
  component: WaiversPage,
})

function WaiversPage() {
  const { leagueId } = Route.useParams()
  const leagueQuery = useQuery(leagueDetailOptions(leagueId))
  const rosterId = leagueQuery.data?.user_roster_id ?? 0
  const waiverQuery = useQuery(waiverRecommendationsOptions(leagueId, rosterId))

  if (leagueQuery.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-56 w-full" />
      </div>
    )
  }

  if (leagueQuery.isError || !leagueQuery.data) {
    return (
      <p className="text-sm text-muted-foreground">
        League data unavailable. Try refreshing or check the backend connection.
      </p>
    )
  }

  if (!rosterId) {
    return (
      <Card className="border-dashed border-border/45">
        <CardHeader>
          <p className="terminal-label text-muted-foreground">Waiver Wire</p>
          <CardTitle>Waiver Intelligence Unavailable</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-6 text-muted-foreground">
            This league is not linked to a user roster yet, so there is no FAAB posture to score.
          </p>
        </CardContent>
      </Card>
    )
  }

  if (waiverQuery.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-56 w-full" />
      </div>
    )
  }

  if (waiverQuery.isError || !waiverQuery.data) {
    return (
      <Card>
        <CardHeader>
          <p className="terminal-label text-muted-foreground">Waiver Wire</p>
          <CardTitle>Waiver Intelligence Unavailable</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-6 text-muted-foreground">
            Waiver intelligence could not be loaded. Ingest data may be incomplete. Try refreshing
            or re-running ingest for this league.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-8">
      <WaiverIntelHeader
        directionLabel={leagueQuery.data.direction_label}
        waiver={waiverQuery.data}
      />
      <WaiverPlayerList
        recommendations={waiverQuery.data.recommendations}
        dataFreshnessWarning={waiverQuery.data.data_freshness_warning}
      />
    </div>
  )
}
