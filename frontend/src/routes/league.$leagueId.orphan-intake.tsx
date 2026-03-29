import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"

import {
  actionPlanOptions,
  hygieneOptions,
  leagueDetailOptions,
  lineupScoreOptions,
  pickListOptions,
  runOrphanIntake,
} from "@/api/queries"
import { AgeCurveRiskPanel } from "@/components/orphan/AgeCurveRiskPanel"
import { DeadRosterPanel } from "@/components/orphan/DeadRosterPanel"
import { LineupViabilityPanel } from "@/components/orphan/LineupViabilityPanel"
import { LiquidationOptionsPanel } from "@/components/orphan/LiquidationOptionsPanel"
import { OrphanIntakeStatusCard } from "@/components/orphan/OrphanIntakeStatusCard"
import { PickCapitalPanel } from "@/components/orphan/PickCapitalPanel"
import { ThirtyDayActionPlanCard } from "@/components/orphan/ThirtyDayActionPlanCard"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

export const Route = createFileRoute("/league/$leagueId/orphan-intake")({
  component: OrphanIntakePage,
})

function OrphanIntakePage() {
  const { leagueId } = Route.useParams()
  const leagueQuery = useQuery(leagueDetailOptions(leagueId))
  const rosterId = leagueQuery.data?.user_roster_id ?? 0
  const intakeQuery = useQuery({
    queryKey: ["orphan-intake", leagueId, rosterId],
    queryFn: () => runOrphanIntake(leagueId, rosterId),
    enabled: rosterId > 0,
    staleTime: 60 * 1000,
  })
  const actionPlanQuery = useQuery(actionPlanOptions(leagueId, rosterId))
  const hygieneQuery = useQuery(hygieneOptions(leagueId, rosterId))
  const lineupQuery = useQuery(lineupScoreOptions(leagueId, rosterId))
  const pickQuery = useQuery(pickListOptions(leagueId, rosterId))

  if (leagueQuery.isLoading || intakeQuery.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-28 w-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
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

  if (!rosterId || intakeQuery.isError || !intakeQuery.data) {
    return (
      <Card className="border-dashed border-border/45">
        <CardHeader>
          <p className="terminal-label text-muted-foreground">Orphan Intake</p>
          <CardTitle>Orphan Intake Not Available</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-6 text-muted-foreground">
            Orphan intake needs a linked roster plus current lineup and valuation data before it can
            score a first-month action plan.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-8">
      <OrphanIntakeStatusCard intake={intakeQuery.data} />
      <AgeCurveRiskPanel intake={intakeQuery.data} />
      <PickCapitalPanel
        intake={intakeQuery.data}
        picks={pickQuery.data?.picks ?? []}
      />
      <DeadRosterPanel suggestions={hygieneQuery.data?.suggestions ?? []} />
      <LineupViabilityPanel lineup={lineupQuery.data ?? null} />
      <LiquidationOptionsPanel
        intake={intakeQuery.data}
        plan={actionPlanQuery.data ?? null}
      />
      <ThirtyDayActionPlanCard plan={actionPlanQuery.data ?? null} />
    </div>
  )
}
