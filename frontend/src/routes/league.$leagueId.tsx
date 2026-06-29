import { useEffect, useState } from "react"

import { useQuery } from "@tanstack/react-query"
import {
  Link,
  Outlet,
  createFileRoute,
  useLocation,
} from "@tanstack/react-router"

import {
  calendarContextOptions,
  leagueDetailOptions,
  leagueRosterOptions,
  lineupScoreOptions,
} from "@/api/queries"
import { LeagueOverviewPanels } from "@/components/league/LeagueOverviewPanels"
import { LeagueRosterSelector } from "@/components/league/LeagueRosterSelector"
import { CalendarStateBadge } from "@/components/context/CalendarStateBadge"
import {
  DirectionReadPopover,
  HoverTrigger,
  Popout,
} from "@/components/DirectionReadPopover"
import { LineupStrengthCard } from "@/components/lineup/LineupStrengthCard"
import { WeeklyEdgePanel } from "@/components/weekly/WeeklyEdgePanel"
import { SnapshotStatus } from "@/components/SnapshotStatus"
import { SnapshotComparisonSheet } from "@/components/SnapshotComparisonSheet"
import { Badge } from "@/components/ui/badge"
import { Button, buttonClasses } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  LeagueRosterSelectionProvider,
  persistStoredLeagueRosterId,
  readStoredLeagueRosterId,
} from "@/lib/league-roster-selection"

export const Route = createFileRoute("/league/$leagueId")({
  validateSearch: (search: Record<string, unknown>) => ({
    rosterId:
      typeof search.rosterId === "number"
        ? search.rosterId
        : typeof search.rosterId === "string"
          ? Number(search.rosterId) || undefined
          : undefined,
    focus: search.focus === "weekly" ? "weekly" : undefined,
    startPlayerId:
      typeof search.startPlayerId === "string" ? search.startPlayerId : undefined,
    sitPlayerId:
      typeof search.sitPlayerId === "string" ? search.sitPlayerId : undefined,
    position: typeof search.position === "string" ? search.position : undefined,
  }),
  component: LeagueDetailPage,
})

function titleWindowLabelContext(
  label: "Peak Window" | "Fading Window" | "Outside Window",
) {
  switch (label) {
    case "Peak Window":
      return "This roster has enough ceiling, stability, and depth to push for a title without needing perfect weekly luck."
    case "Fading Window":
      return "This roster is still competitive, but it is missing enough insulation that the title path looks thinner than a true peak contender."
    case "Outside Window":
      return "This roster does not currently project as a credible title build and needs material lineup improvement before pressing in."
  }
}

function titleWindowScoreWord(score: number) {
  if (score >= 0.6) return "strong"
  if (score >= 0.3) return "mixed"
  return "thin"
}

function LeagueDetailPage() {
  const { leagueId } = Route.useParams()
  return <LeagueDetailPageContent key={leagueId} leagueId={leagueId} />
}

function LeagueDetailPageContent({ leagueId }: { leagueId: string }) {
  const location = useLocation()
  const search = Route.useSearch()
  const [requestedRosterId, setRequestedRosterId] = useState<number | null>(
    () => search.rosterId ?? readStoredLeagueRosterId(leagueId),
  )
  const query = useQuery(leagueDetailOptions(leagueId, requestedRosterId))
  const rosterOptionsQuery = useQuery(leagueRosterOptions(leagueId))
  const calendarQuery = useQuery(calendarContextOptions(leagueId))
  const lineupQuery = useQuery(
    lineupScoreOptions(leagueId, query.data?.user_roster_id ?? 0),
  )
  const [comparisonOpen, setComparisonOpen] = useState(false)

  useEffect(() => {
    persistStoredLeagueRosterId(leagueId, requestedRosterId)
  }, [leagueId, requestedRosterId])

  useEffect(() => {
    if (search.rosterId && search.rosterId !== requestedRosterId) {
      setRequestedRosterId(search.rosterId)
    }
  }, [requestedRosterId, search.rosterId])

  useEffect(() => {
    if (requestedRosterId !== null || !query.data?.user_roster_id) {
      return
    }
    setRequestedRosterId(query.data.user_roster_id)
  }, [query.data?.user_roster_id, requestedRosterId])

  useEffect(() => {
    if (!rosterOptionsQuery.data || requestedRosterId === null) {
      return
    }
    if (
      rosterOptionsQuery.data.some(
        (option) => option.roster_id === requestedRosterId,
      )
    ) {
      return
    }
    setRequestedRosterId(
      query.data?.user_roster_id ??
        rosterOptionsQuery.data[0]?.roster_id ??
        null,
    )
  }, [query.data?.user_roster_id, requestedRosterId, rosterOptionsQuery.data])

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
  const selectedRosterId = requestedRosterId ?? league.user_roster_id ?? null
  const selectionContext = {
    leagueId,
    requestedRosterId,
    setRequestedRosterId,
    rosterOptions: rosterOptionsQuery.data ?? [],
    league,
  }
  const leaguePath = `/league/${leagueId}`
  const isOverviewRoute = location.pathname === leaguePath
  const isComparisonRoute = location.pathname === `${leaguePath}/comparison`
  const isManagersRoute = location.pathname.startsWith(`${leaguePath}/managers`)
  const isTradeHistoryRoute = location.pathname === `${leaguePath}/trade-history`
  const isDraftGradesRoute = location.pathname === `${leaguePath}/draft-grades`
  const isLeagueOpsRoute = location.pathname === `${leaguePath}/league-ops`
  const isPlayerRankingsRoute =
    location.pathname === `${leaguePath}/player-rankings`
  const isRookieBoardRoute = location.pathname === `${leaguePath}/rookie-board`
  const isRosterMovesRoute = location.pathname === `${leaguePath}/roster-moves`
  const isWaiversRoute = location.pathname === `${leaguePath}/waivers`
  const isStartupRoute = location.pathname === `${leaguePath}/startup`
  const isOrphanIntakeRoute =
    location.pathname === `${leaguePath}/orphan-intake`
  const titleWindowData = lineupQuery.data ?? null
  const titleWindowBadgeClass =
    titleWindowData?.title_window_label === "Peak Window"
      ? "border-accent/20 bg-accent/10 text-accent-foreground"
      : titleWindowData?.title_window_label === "Fading Window"
        ? "border-primary/25 bg-primary/12 text-primary"
        : "border-border/60 bg-transparent text-muted-foreground"
  const ceilingWord = titleWindowData
    ? titleWindowData.ceiling_score >= 0.6
      ? "elite"
      : titleWindowData.ceiling_score >= 0.3
        ? "competitive"
        : "below the field"
    : null

  return (
    <LeagueRosterSelectionProvider value={selectionContext}>
      <div className="space-y-8">
        <Card className="overflow-visible">
          <CardHeader
            className={
              isOverviewRoute
                ? "grid gap-8 lg:grid-cols-[minmax(280px,440px)_minmax(0,1fr)]"
                : "grid gap-4 p-4 lg:grid-cols-[minmax(260px,420px)_minmax(0,1fr)] lg:items-start lg:p-5"
            }
          >
            <div className={isOverviewRoute ? "space-y-3" : "space-y-3"}>
              <div className="flex flex-wrap items-center gap-3">
                <div>
                  <p className="terminal-label text-muted-foreground">
                    League Briefing
                  </p>
                  <CardTitle
                    className={
                      isOverviewRoute ? "mt-2 text-3xl" : "mt-1 text-xl"
                    }
                  >
                    {league.league_name}
                  </CardTitle>
                  {league.user_roster_name ? (
                    <p className="mt-1 text-sm text-muted-foreground">
                      Viewing {league.user_roster_name}.
                    </p>
                  ) : null}
                </div>
                {calendarQuery.data ? (
                  <CalendarStateBadge state={calendarQuery.data.active_state} />
                ) : null}
                {titleWindowData ? (
                  <HoverTrigger
                    className="inline-flex"
                    popout={
                      <Popout title={titleWindowData.title_window_label}>
                        <p>
                          {titleWindowLabelContext(
                            titleWindowData.title_window_label,
                          )}
                        </p>
                        <p>
                          Composite title score:{" "}
                          <span className="text-foreground">
                            {titleWindowData.title_window_composite.toFixed(2)}
                          </span>
                          . Ceiling reads{" "}
                          {titleWindowScoreWord(titleWindowData.ceiling_score)},
                          stability reads{" "}
                          {titleWindowScoreWord(
                            titleWindowData.stability_score,
                          )}
                          , and depth reads{" "}
                          {titleWindowScoreWord(titleWindowData.depth_score)}.
                        </p>
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge variant="outline">
                            Ceiling {titleWindowData.ceiling_score.toFixed(2)}
                          </Badge>
                          <Badge variant="outline">
                            Stability{" "}
                            {titleWindowData.stability_score.toFixed(2)}
                          </Badge>
                          <Badge variant="outline">
                            Depth {titleWindowData.depth_score.toFixed(2)}
                          </Badge>
                        </div>
                      </Popout>
                    }
                  >
                    <Badge className={titleWindowBadgeClass}>
                      {titleWindowData.title_window_label}
                    </Badge>
                  </HoverTrigger>
                ) : null}
              </div>
              {isOverviewRoute ? (
                <div>
                  <DirectionReadPopover
                    directionRead={league.direction_read}
                    directionLabel={league.direction_label}
                    directionAlternates={league.direction_alternates}
                    directionNote={league.direction_note}
                    directionReasoning={league.direction_reasoning}
                    directionFitFlags={league.direction_fit_flags}
                  />
                  {ceilingWord ? (
                    <p className="mt-3 text-xs text-muted-foreground">
                      Starter ceiling is {ceilingWord}.
                    </p>
                  ) : null}
                  <div className="mt-4">
                    <LeagueRosterSelector
                      options={rosterOptionsQuery.data ?? []}
                      value={requestedRosterId ?? league.user_roster_id}
                      onChange={setRequestedRosterId}
                      disabled={rosterOptionsQuery.isLoading}
                    />
                  </div>
                </div>
              ) : (
                <LeagueRosterSelector
                  options={rosterOptionsQuery.data ?? []}
                  value={requestedRosterId ?? league.user_roster_id}
                  onChange={setRequestedRosterId}
                  disabled={rosterOptionsQuery.isLoading}
                />
              )}
            </div>
            <div className="space-y-4 lg:pt-1">
              <div className="flex flex-wrap items-center justify-start gap-2 lg:justify-end">
                <Link
                  to="/draft-room"
                  search={{ leagueId, pickSlot: 1 }}
                  className={buttonClasses({
                    variant: "outline",
                    size: "sm",
                    className: "h-9",
                  })}
                >
                  Enter Draft Room
                </Link>
                <Link
                  to="/trades"
                  search={{
                    leagueId,
                    userRosterId: league.user_roster_id ?? undefined,
                  }}
                  className={buttonClasses({ size: "sm", className: "h-9" })}
                >
                  Evaluate Trade
                </Link>
              </div>

              <nav aria-label="League sections" className="space-y-3">
                <div className="flex flex-wrap justify-start gap-2 lg:justify-end">
                  <Link
                    to="/league/$leagueId"
                    params={{ leagueId }}
                    className={buttonClasses({
                      variant: isOverviewRoute ? "default" : "outline",
                      size: "sm",
                      className: "h-9 px-3",
                    })}
                  >
                    Overview
                  </Link>
                  <Link
                    to="/league/$leagueId/comparison"
                    params={{ leagueId }}
                    className={buttonClasses({
                      variant: isComparisonRoute ? "default" : "outline",
                      size: "sm",
                      className: "h-9 px-3",
                    })}
                  >
                    Comparison
                  </Link>
                  <Link
                    to="/league/$leagueId/managers"
                    params={{ leagueId }}
                    className={buttonClasses({
                      variant: isManagersRoute ? "default" : "outline",
                      size: "sm",
                      className: "h-9 px-3",
                    })}
                  >
                    Managers
                  </Link>
                  <Link
                    to="/league/$leagueId/trade-history"
                    params={{ leagueId }}
                    className={buttonClasses({
                      variant: isTradeHistoryRoute ? "default" : "outline",
                      size: "sm",
                      className: "h-9 px-3",
                    })}
                  >
                    Trade History
                  </Link>
                  <Link
                    to="/league/$leagueId/draft-grades"
                    params={{ leagueId }}
                    className={buttonClasses({
                      variant: isDraftGradesRoute ? "default" : "outline",
                      size: "sm",
                      className: "h-9 px-3",
                    })}
                  >
                    Draft Grades
                  </Link>
                  <Link
                    to="/league/$leagueId/roster-moves"
                    params={{ leagueId }}
                    className={buttonClasses({
                      variant: isRosterMovesRoute ? "default" : "outline",
                      size: "sm",
                      className: "h-9 px-3",
                    })}
                  >
                    Roster Moves
                  </Link>
                  <Link
                    to="/league/$leagueId/player-rankings"
                    params={{ leagueId }}
                    className={buttonClasses({
                      variant: isPlayerRankingsRoute ? "default" : "outline",
                      size: "sm",
                      className: "h-9 px-3",
                    })}
                  >
                    Rankings
                  </Link>
                </div>

                <div className="flex flex-wrap justify-start gap-1.5 lg:justify-end">
                  <Link
                    to="/league/$leagueId/league-ops"
                    params={{ leagueId }}
                    className={buttonClasses({
                      variant: isLeagueOpsRoute ? "secondary" : "ghost",
                      size: "sm",
                      className: "h-8 px-2.5",
                    })}
                  >
                    League Ops
                  </Link>
                  <Link
                    to="/league/$leagueId/rookie-board"
                    params={{ leagueId }}
                    className={buttonClasses({
                      variant: isRookieBoardRoute ? "secondary" : "ghost",
                      size: "sm",
                      className: "h-8 px-2.5",
                    })}
                  >
                    Rookie Board
                  </Link>
                  <Link
                    to="/league/$leagueId/waivers"
                    params={{ leagueId }}
                    className={buttonClasses({
                      variant: isWaiversRoute ? "secondary" : "ghost",
                      size: "sm",
                      className: "h-8 px-2.5",
                    })}
                  >
                    Waivers
                  </Link>
                  <Link
                    to="/league/$leagueId/startup"
                    params={{ leagueId }}
                    className={buttonClasses({
                      variant: isStartupRoute ? "secondary" : "ghost",
                      size: "sm",
                      className: `h-8 px-2.5 ${isStartupRoute ? "" : "opacity-60"}`,
                    })}
                  >
                    Startup
                  </Link>
                  <Link
                    to="/league/$leagueId/orphan-intake"
                    params={{ leagueId }}
                    className={buttonClasses({
                      variant: isOrphanIntakeRoute ? "secondary" : "ghost",
                      size: "sm",
                      className: "h-8 px-2.5",
                    })}
                  >
                    Orphan Intake
                  </Link>
                </div>
              </nav>
            </div>
          </CardHeader>
          <CardContent
            className={`flex flex-wrap items-center justify-between gap-3 border-t border-border/40 ${
              isOverviewRoute ? "pt-5" : "p-4 lg:p-5"
            }`}
          >
            <SnapshotStatus
              leagueId={leagueId}
              lastSnapshotAt={league.last_snapshot_at}
            />
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

        {isOverviewRoute && selectedRosterId ? (
          <LineupStrengthCard
            leagueId={leagueId}
            rosterId={selectedRosterId}
          />
        ) : null}

        {isOverviewRoute && selectedRosterId ? (
          <WeeklyEdgePanel
            leagueId={leagueId}
            rosterId={selectedRosterId}
            focus={search.focus}
            startPlayerId={search.startPlayerId}
            sitPlayerId={search.sitPlayerId}
            position={search.position}
          />
        ) : null}

        {isOverviewRoute ? (
          <LeagueOverviewPanels league={league} leagueId={leagueId} />
        ) : (
          <Outlet />
        )}
        {league.user_roster_id ? (
          <SnapshotComparisonSheet
            leagueId={leagueId}
            rosterId={league.user_roster_id}
            open={comparisonOpen}
            onOpenChange={setComparisonOpen}
          />
        ) : null}
      </div>
    </LeagueRosterSelectionProvider>
  )
}
