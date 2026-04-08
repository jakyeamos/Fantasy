import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"

import { startupContextOptions } from "@/api/queries"
import { StartupBuildTemplatePanel } from "@/components/startup/StartupBuildTemplatePanel"
import { StartupDraftContextCard } from "@/components/startup/StartupDraftContextCard"
import { StartupPickValuationList } from "@/components/startup/StartupPickValuationList"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { useLeagueRosterSelection } from "@/lib/league-roster-selection"

export const Route = createFileRoute("/league/$leagueId/startup")({
  component: StartupPage,
})

function StartupPage() {
  const { leagueId, league } = useLeagueRosterSelection()
  const rosterId = league.user_roster_id ?? 0
  const startupQuery = useQuery(startupContextOptions(leagueId, rosterId))

  if (startupQuery.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-56 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    )
  }

  if (startupQuery.isError || !startupQuery.data || !startupQuery.data.startup_mode_available) {
    return (
      <Card className="border-dashed border-border/45">
        <CardHeader>
          <p className="terminal-label text-muted-foreground">Startup Draft</p>
          <CardTitle>Startup Data Unavailable</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-6 text-muted-foreground">
            Startup draft mode only appears when the league draft is still in `pre_draft` or
            `drafting`.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-8">
      <StartupDraftContextCard
        leagueName={league.league_name}
        context={startupQuery.data}
      />
      <StartupPickValuationList picks={startupQuery.data.pick_valuations} />
      <StartupBuildTemplatePanel buildTemplate={startupQuery.data.build_template} />
    </div>
  )
}
