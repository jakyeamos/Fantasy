import { useEffect, useState } from "react"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Link, Outlet, createFileRoute, useLocation } from "@tanstack/react-router"

import type { LeagueDraftOrderRule } from "@/api/types"
import {
  calendarContextOptions,
  draftOrderRuleOptions,
  leagueDetailOptions,
  saveDraftOrderRule,
} from "@/api/queries"
import { CalendarContextPanel } from "@/components/context/CalendarContextPanel"
import { CalendarStateBadge } from "@/components/context/CalendarStateBadge"
import { ConcentrationAlertBanner } from "@/components/ConcentrationAlertBanner"
import { ExploitWindowPanel } from "@/components/ExploitWindowPanel"
import { FormatWarningBanner } from "@/components/FormatWarningBanner"
import { LineupStrengthCard } from "@/components/lineup/LineupStrengthCard"
import { RosterHygienePanel } from "@/components/lineup/RosterHygienePanel"
import { TaxiConfigForm } from "@/components/lineup/TaxiConfigForm"
import { TaxiIRSlotSummary } from "@/components/lineup/TaxiIRSlotSummary"
import { TitleWindowPanel } from "@/components/lineup/TitleWindowPanel"
import { RisersFallersList } from "@/components/RisersFallersList"
import { SnapshotStatus } from "@/components/SnapshotStatus"
import { SnapshotComparisonSheet } from "@/components/SnapshotComparisonSheet"
import { LeaguePickList } from "@/components/picks/LeaguePickList"
import { Badge } from "@/components/ui/badge"
import { Button, buttonClasses } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Skeleton } from "@/components/ui/skeleton"
import { directionReadBadgeVariant, formatModelLabel } from "@/lib/utils"

export const Route = createFileRoute("/league/$leagueId")({
  component: LeagueDetailPage,
})

const basisLabels: Record<LeagueDraftOrderRule["non_playoff_basis"], string> = {
  inverse_standings: "Inverse standings",
  max_points_for: "Max points for",
}

const playoffOrderingLabels: Record<LeagueDraftOrderRule["playoff_ordering"], string> = {
  by_finish: "By playoff finish",
  by_record: "By regular-season record",
  by_points_for: "By regular-season points for",
}

const tiebreakerLabels: Record<LeagueDraftOrderRule["tiebreaker"], string> = {
  points_against: "Points against",
  points_for: "Points for",
  commissioner: "Commissioner discretion",
}

function DraftOrderRuleForm({ leagueId }: { leagueId: string }) {
  const queryClient = useQueryClient()
  const ruleQuery = useQuery(draftOrderRuleOptions(leagueId))
  const rule = ruleQuery.data?.rule ?? null
  const [editing, setEditing] = useState(false)
  const [basis, setBasis] = useState<LeagueDraftOrderRule["non_playoff_basis"] | "">("")
  const [playoffOrdering, setPlayoffOrdering] = useState<LeagueDraftOrderRule["playoff_ordering"] | "">("")
  const [tiebreaker, setTiebreaker] = useState<LeagueDraftOrderRule["tiebreaker"] | "">("")

  useEffect(() => {
    if (editing) return
    if (rule) {
      setBasis(rule.non_playoff_basis)
      setPlayoffOrdering(rule.playoff_ordering)
      setTiebreaker(rule.tiebreaker)
      return
    }
    setBasis("")
    setPlayoffOrdering("")
    setTiebreaker("")
  }, [editing, rule])

  const saveMutation = useMutation({
    mutationFn: (nextRule: LeagueDraftOrderRule) => saveDraftOrderRule(leagueId, nextRule),
    onSuccess: async (data) => {
      queryClient.setQueryData(["picks", leagueId, "draft-order-rule"], data)
      await queryClient.invalidateQueries({ queryKey: ["picks", leagueId] })
      setEditing(false)
    },
  })

  const allFieldsFilled = basis !== "" && playoffOrdering !== "" && tiebreaker !== ""
  const showSummary = rule !== null && !editing

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!allFieldsFilled) return
    saveMutation.mutate({
      non_playoff_basis: basis,
      playoff_ordering: playoffOrdering,
      tiebreaker,
    })
  }

  if (ruleQuery.isLoading && rule === null) {
    return (
      <Card id="draft-order-rule">
        <CardHeader>
          <CardTitle>Draft Order Rule</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Loading league draft-order settings...</p>
        </CardContent>
      </Card>
    )
  }

  if (showSummary) {
    return (
      <Card id="draft-order-rule">
        <CardHeader className="flex flex-row items-start justify-between gap-4">
          <div>
            <CardTitle>Draft Order Rule</CardTitle>
            <p className="mt-2 text-sm text-muted-foreground">
              This league&apos;s pick projection rule is configured and active.
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={() => setEditing(true)}>
            Edit
          </Button>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <p>
            <span className="text-muted-foreground">Non-playoff ordering:</span>{" "}
            {basisLabels[rule.non_playoff_basis]}
          </p>
          <p>
            <span className="text-muted-foreground">Playoff team ordering:</span>{" "}
            {playoffOrderingLabels[rule.playoff_ordering]}
          </p>
          <p>
            <span className="text-muted-foreground">Tiebreaker:</span>{" "}
            {tiebreakerLabels[rule.tiebreaker]}
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card id="draft-order-rule">
      <CardHeader>
        <CardTitle>Draft Order Rule</CardTitle>
        <p className="mt-2 text-sm text-muted-foreground">
          Pick values stay blocked until this league&apos;s draft-order rule is fully configured.
        </p>
      </CardHeader>
      <CardContent>
        <form className="space-y-6" onSubmit={handleSubmit}>
          {ruleQuery.isError ? (
            <p className="rounded-lg border border-destructive/25 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              The current rule could not be loaded. You can still save a new one.
            </p>
          ) : null}

          <div className="space-y-3">
            <Label>Non-playoff order basis</Label>
            <RadioGroup className="gap-3">
              <label className="flex items-start gap-3 rounded-lg border border-border/60 bg-card/60 p-3">
                <RadioGroupItem
                  name="non-playoff-basis"
                  value="inverse_standings"
                  checked={basis === "inverse_standings"}
                  onChange={() => setBasis("inverse_standings")}
                />
                <div className="space-y-1">
                  <span className="text-sm font-semibold">Inverse standings</span>
                  <p className="text-xs text-muted-foreground">
                    Worst record gets the earliest draft slot.
                  </p>
                </div>
              </label>
              <label className="flex items-start gap-3 rounded-lg border border-border/60 bg-card/60 p-3">
                <RadioGroupItem
                  name="non-playoff-basis"
                  value="max_points_for"
                  checked={basis === "max_points_for"}
                  onChange={() => setBasis("max_points_for")}
                />
                <div className="space-y-1">
                  <span className="text-sm font-semibold">Max points for</span>
                  <p className="text-xs text-muted-foreground">
                    Lower season-long points for gets the earlier non-playoff slot.
                  </p>
                </div>
              </label>
            </RadioGroup>
          </div>

          <div className="block space-y-2">
            <Label htmlFor="playoff-ordering">Playoff team ordering</Label>
            <select
              id="playoff-ordering"
              value={playoffOrdering}
              onChange={(event) =>
                setPlayoffOrdering(
                  event.target.value as LeagueDraftOrderRule["playoff_ordering"] | "",
                )
              }
              className="h-11 w-full rounded-lg border border-border bg-card px-3 text-sm"
            >
              <option value="">Select playoff ordering</option>
              <option value="by_finish">By playoff finish</option>
              <option value="by_record">By regular-season record</option>
              <option value="by_points_for">By regular-season points for</option>
            </select>
          </div>

          <div className="block space-y-2">
            <Label htmlFor="tiebreaker">Tiebreaker</Label>
            <select
              id="tiebreaker"
              value={tiebreaker}
              onChange={(event) =>
                setTiebreaker(event.target.value as LeagueDraftOrderRule["tiebreaker"] | "")
              }
              className="h-11 w-full rounded-lg border border-border bg-card px-3 text-sm"
            >
              <option value="">Select tiebreaker</option>
              <option value="points_against">Points against</option>
              <option value="points_for">Points for</option>
              <option value="commissioner">Commissioner discretion</option>
            </select>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Button type="submit" disabled={!allFieldsFilled || saveMutation.isPending}>
              {saveMutation.isPending ? "Saving..." : rule ? "Save Changes" : "Save Rule"}
            </Button>
            {rule ? (
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setEditing(false)
                  saveMutation.reset()
                }}
              >
                Cancel
              </Button>
            ) : null}
            {saveMutation.isError ? (
              <p className="text-sm text-destructive">Failed to save the draft-order rule.</p>
            ) : null}
          </div>
        </form>
      </CardContent>
    </Card>
  )
}

function LeagueDetailPage() {
  const { leagueId } = Route.useParams()
  const location = useLocation()
  const query = useQuery(leagueDetailOptions(leagueId))
  const calendarQuery = useQuery(calendarContextOptions(leagueId))
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
  const leaguePath = `/league/${leagueId}`
  const isOverviewRoute = location.pathname === leaguePath
  const isManagersRoute = location.pathname.startsWith(`${leaguePath}/managers`)
  const isRookieBoardRoute = location.pathname === `${leaguePath}/rookie-board`
  const isWaiversRoute = location.pathname === `${leaguePath}/waivers`
  const isStartupRoute = location.pathname === `${leaguePath}/startup`
  const isOrphanIntakeRoute = location.pathname === `${leaguePath}/orphan-intake`

  return (
    <div className="space-y-8">
      <Card className="overflow-hidden">
        <CardHeader className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-3">
              <div>
                <p className="terminal-label text-muted-foreground">League briefing</p>
                <CardTitle className="mt-2 text-3xl">{league.league_name}</CardTitle>
              </div>
              <Badge variant={directionReadBadgeVariant(league.direction_read)}>
                {league.direction_read}
              </Badge>
              {calendarQuery.data ? (
                <CalendarStateBadge state={calendarQuery.data.active_state} />
              ) : null}
            </div>
            <div>
              <p className="font-headline text-2xl font-extrabold">
                {formatModelLabel(league.direction_label)}
              </p>
              {league.direction_note ? (
                <p className="mt-3 max-w-3xl text-sm leading-6 text-muted-foreground">
                  {league.direction_note}
                </p>
              ) : null}
              {league.direction_alternates.length > 0 ? (
                <>
                  <p className="mt-4 terminal-label text-muted-foreground">
                    Nearby paths
                  </p>
                  <p className="mt-1 text-sm leading-6 text-muted-foreground">
                    {league.direction_alternates.map((label) => formatModelLabel(label)).join(" • ")}
                  </p>
                </>
              ) : null}
              <p className="mt-3 terminal-label text-muted-foreground">
                Roster note
              </p>
              <p className="mt-1 max-w-3xl text-sm leading-6 text-muted-foreground">
                {league.primary_weakness}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex flex-wrap gap-2">
              <Link
                to="/league/$leagueId"
                params={{ leagueId }}
                className={buttonClasses({
                  variant: isOverviewRoute ? "default" : "outline",
                })}
              >
                Overview
              </Link>
              <Link
                to="/league/$leagueId/managers"
                params={{ leagueId }}
                className={buttonClasses({
                  variant: isManagersRoute ? "default" : "outline",
                })}
              >
                Managers
              </Link>
              <Link
                to="/league/$leagueId/rookie-board"
                params={{ leagueId }}
                className={buttonClasses({
                  variant: isRookieBoardRoute ? "default" : "outline",
                })}
              >
                Rookie Board
              </Link>
              <Link
                to="/league/$leagueId/waivers"
                params={{ leagueId }}
                className={buttonClasses({
                  variant: isWaiversRoute ? "default" : "outline",
                })}
              >
                Waivers
              </Link>
              <Link
                to="/league/$leagueId/startup"
                params={{ leagueId }}
                className={buttonClasses({
                  variant: isStartupRoute ? "default" : "outline",
                })}
              >
                Startup Draft
              </Link>
              <Link
                to="/league/$leagueId/orphan-intake"
                params={{ leagueId }}
                className={buttonClasses({
                  variant: isOrphanIntakeRoute ? "default" : "outline",
                })}
              >
                Orphan Intake
              </Link>
            </div>
            <div className="flex flex-wrap gap-2">
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
          </div>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center justify-between gap-3 border-t border-border/40 pt-5">
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

      {calendarQuery.data ? (
        <CalendarContextPanel context={calendarQuery.data} />
      ) : null}

      {/* Phase 11 lineup intelligence panels render above overview summary cards. */}
      {isOverviewRoute && league.user_roster_id ? (
        <>
          <TitleWindowPanel leagueId={leagueId} rosterId={league.user_roster_id} />
          <LineupStrengthCard leagueId={leagueId} rosterId={league.user_roster_id} />
          <RosterHygienePanel leagueId={leagueId} rosterId={league.user_roster_id} />
        </>
      ) : null}

      {isOverviewRoute ? (
        <section className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader className="pb-2">
              <p className="terminal-label text-muted-foreground">Exploit windows</p>
            </CardHeader>
            <CardContent>
              <p className="font-headline text-3xl font-extrabold tracking-tight">
                {league.exploit_windows.length}
              </p>
              <p className="mt-2 text-sm text-muted-foreground">
                Managers currently showing live behavioral triggers.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <p className="terminal-label text-muted-foreground">Market movement</p>
            </CardHeader>
            <CardContent>
              <p className="font-headline text-3xl font-extrabold tracking-tight">
                {league.risers.length + league.fallers.length}
              </p>
              <p className="mt-2 text-sm text-muted-foreground">
                Player valuation changes surfaced in the latest ingest.
              </p>
            </CardContent>
          </Card>
        </section>
      ) : null}

      {isOverviewRoute ? (
        <>
          <Card>
            <CardHeader className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <CardTitle>Workflow Shortcuts</CardTitle>
                <p className="mt-2 text-sm text-muted-foreground">
                  Jump from the league briefing into managers, trades, and draft views.
                </p>
              </div>
            </CardHeader>
            <CardContent className="flex flex-wrap items-center gap-3">
              <Link
                to="/trades"
                search={{ leagueId }}
                className={buttonClasses({ variant: "outline" })}
              >
                Open Trade Lab
              </Link>
              <Link
                to="/league/$leagueId/managers"
                params={{ leagueId }}
                className={buttonClasses({ variant: "outline" })}
              >
                Review Dossiers
              </Link>
            </CardContent>
          </Card>

          <FormatWarningBanner leagueId={leagueId} />
          <ConcentrationAlertBanner
            leagueId={leagueId}
            userRosterPlayerIds={league.user_roster_player_ids}
          />
          <RisersFallersList risers={league.risers} fallers={league.fallers} />
          <LeaguePickList leagueId={leagueId} rosterId={league.user_roster_id} />
          <DraftOrderRuleForm leagueId={leagueId} />
          <ExploitWindowPanel leagueId={leagueId} windows={league.exploit_windows} />
          <TaxiIRSlotSummary leagueId={leagueId} rosterId={league.user_roster_id ?? 0} />
          <TaxiConfigForm leagueId={leagueId} />
          {league.user_roster_id ? (
            <SnapshotComparisonSheet
              leagueId={leagueId}
              rosterId={league.user_roster_id}
              open={comparisonOpen}
              onOpenChange={setComparisonOpen}
            />
          ) : null}
        </>
      ) : (
        <Outlet />
      )}
    </div>
  )
}
