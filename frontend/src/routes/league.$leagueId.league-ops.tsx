import { createFileRoute } from "@tanstack/react-router"

import { DraftOrderRuleForm } from "@/components/league/DraftOrderRuleForm"
import { ExploitWindowPanel } from "@/components/ExploitWindowPanel"
import { FormatWarningBanner } from "@/components/FormatWarningBanner"
import { TaxiConfigForm } from "@/components/lineup/TaxiConfigForm"
import { TaxiIRSlotSummary } from "@/components/lineup/TaxiIRSlotSummary"
import { LeaguePickList } from "@/components/picks/LeaguePickList"
import { Card, CardHeader, CardTitle } from "@/components/ui/card"
import { useLeagueRosterSelection } from "@/lib/league-roster-selection"

export const Route = createFileRoute("/league/$leagueId/league-ops")({
  component: LeagueOpsPage,
})

function LeagueOpsPage() {
  const { leagueId, league } = useLeagueRosterSelection()

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>League Ops</CardTitle>
          <p className="mt-2 text-sm text-muted-foreground">
            Pick inventory, exploit windows, draft-order rules, and taxi
            configuration for this league.
          </p>
        </CardHeader>
      </Card>

      <FormatWarningBanner leagueId={leagueId} />
      <LeaguePickList leagueId={leagueId} rosterId={league.user_roster_id} />
      <ExploitWindowPanel
        leagueId={leagueId}
        windows={league.exploit_windows}
      />
      <DraftOrderRuleForm leagueId={leagueId} />
      <TaxiIRSlotSummary
        leagueId={leagueId}
        rosterId={league.user_roster_id ?? 0}
      />
      <TaxiConfigForm leagueId={leagueId} />
    </div>
  )
}
