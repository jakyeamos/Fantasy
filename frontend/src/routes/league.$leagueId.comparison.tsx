import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"

import { lineupScoreOptions } from "@/api/queries"
import { LeagueCompetitiveLandscapePanel } from "@/components/LeagueCompetitiveLandscapePanel"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useLeagueRosterSelection } from "@/lib/league-roster-selection"

export const Route = createFileRoute("/league/$leagueId/comparison")({
  component: LeagueComparisonPage,
})

function LeagueComparisonPage() {
  const { leagueId, league } = useLeagueRosterSelection()
  const lineupQuery = useQuery(lineupScoreOptions(leagueId, league.user_roster_id ?? 0))

  if (!league.user_roster_id) {
    return (
      <Card
        data-mac-control-id="fantasy.league.comparison-unavailable"
        data-task-state="comparison_unavailable"
      >
        <CardHeader>
          <CardTitle>League Comparison</CardTitle>
          <p className="mt-2 text-sm text-muted-foreground">
            Select a roster before comparing it to the rest of the league.
          </p>
        </CardHeader>
        <CardContent />
      </Card>
    )
  }

  return (
    <div
      data-mac-control-id="fantasy.league.comparison-workspace"
      data-task-state={lineupQuery.isLoading ? "comparison_loading" : "comparison_ready"}
      data-roster-id={league.user_roster_id}
      className="space-y-4"
      role="region"
      aria-label="League comparison workspace"
      aria-busy={lineupQuery.isLoading}
    >
      <Card>
        <CardHeader>
          <CardTitle>League Comparison</CardTitle>
          <p className="mt-2 text-sm text-muted-foreground">
            Win-now, future-value, and title-window comparisons against the rest of the league, with
            matchup outlook shown only during in-season windows.
          </p>
        </CardHeader>
      </Card>

      <LeagueCompetitiveLandscapePanel
        landscape={league.competitive_landscape ?? null}
        lineup={lineupQuery.data ?? null}
        calendarState={league.recommendation_context?.calendar_state ?? null}
      />
    </div>
  )
}
