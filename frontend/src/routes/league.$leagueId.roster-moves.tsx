import { createFileRoute } from "@tanstack/react-router"

import { RosterHygienePanel } from "@/components/lineup/RosterHygienePanel"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useLeagueRosterSelection } from "@/lib/league-roster-selection"

export const Route = createFileRoute("/league/$leagueId/roster-moves")({
  component: LeagueRosterMovesPage,
})

function LeagueRosterMovesPage() {
  const { leagueId, league } = useLeagueRosterSelection()

  if (!league.user_roster_id) {
    return (
      <Card
        data-mac-control-id="fantasy.league.roster-moves-unavailable"
        data-task-state="roster_moves_unavailable"
      >
        <CardHeader>
          <CardTitle>Roster Moves</CardTitle>
          <p className="mt-2 text-sm text-muted-foreground">
            A linked user roster is required before move recommendations can be generated.
          </p>
        </CardHeader>
        <CardContent />
      </Card>
    )
  }

  return (
    <div
      data-mac-control-id="fantasy.league.roster-moves-workspace"
      data-task-state="roster_moves_ready"
      data-roster-id={league.user_roster_id}
      className="space-y-4"
      role="region"
      aria-label="Roster move recommendations"
    >
      <Card>
        <CardHeader>
          <CardTitle>Roster Moves</CardTitle>
          <p className="mt-2 text-sm text-muted-foreground">
            Consolidation ideas, bench triage, stash decisions, and taxi actions for your active
            roster.
          </p>
        </CardHeader>
      </Card>
      <RosterHygienePanel leagueId={leagueId} rosterId={league.user_roster_id} />
    </div>
  )
}
