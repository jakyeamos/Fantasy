import { useQuery } from "@tanstack/react-query"
import { Link, createFileRoute } from "@tanstack/react-router"
import { ArrowRight, Radar, ShieldAlert, Sparkles } from "lucide-react"

import { dashboardSummaryOptions } from "@/api/queries"
import { LeagueCard } from "@/components/LeagueCard"
import { SnapshotStatus } from "@/components/SnapshotStatus"
import { buttonClasses } from "@/components/ui/button"
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
  const actionableLeagues = query.data.filter((league) => league.top_exploit_window).length
  const highConfidenceLeagues = query.data.filter(
    (league) => league.confidence_band === "High",
  ).length

  return (
    <div className="space-y-8">
      <section className="grid gap-4 xl:grid-cols-[minmax(0,1.7fr)_repeat(3,minmax(0,1fr))]">
        <Card className="overflow-hidden">
          <CardHeader className="space-y-4">
            <div className="flex items-center gap-2">
              <Sparkles className="size-4 text-primary" />
              <p className="terminal-label text-primary/85">Global Confidence Index</p>
            </div>
            <div className="space-y-3">
              <h2 className="font-headline text-4xl font-extrabold tracking-tight">
                League intelligence at a glance
              </h2>
              <p className="max-w-3xl text-sm leading-6 text-muted-foreground">
                Scan every league by direction, confidence, exploit window, and
                snapshot freshness. Use this view as the front door into each roster,
                its market posture, and its next likely edge.
              </p>
            </div>
          </CardHeader>
          <CardContent className="flex flex-wrap items-center justify-between gap-4 border-t border-border/40 pt-5">
            <SnapshotStatus lastSnapshotAt={lastSnapshotAt} />
            <Link to="/portfolio" className={buttonClasses({ variant: "outline" })}>
              Open Portfolio
              <ArrowRight className="size-3.5" />
            </Link>
          </CardContent>
        </Card>

        {[
          {
            label: "Tracked Leagues",
            value: String(query.data.length),
            helper: "Active environments",
            icon: Radar,
            tone: "text-primary",
          },
          {
            label: "High Confidence",
            value: String(highConfidenceLeagues),
            helper: "Reliable reads",
            icon: Sparkles,
            tone: "text-accent",
          },
          {
            label: "Exploit Windows",
            value: String(actionableLeagues),
            helper: "Actionable markets",
            icon: ShieldAlert,
            tone: "text-destructive",
          },
        ].map((item) => (
          <Card key={item.label}>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between gap-3">
                <div className={`rounded-lg border border-border/40 bg-card/50 p-2 ${item.tone}`}>
                  <item.icon className="size-4" />
                </div>
                <span className="terminal-label text-muted-foreground">{item.label}</span>
              </div>
            </CardHeader>
            <CardContent>
              <p className="font-headline text-3xl font-extrabold tracking-tight">
                {item.value}
              </p>
              <p className="mt-2 text-sm text-muted-foreground">{item.helper}</p>
            </CardContent>
          </Card>
        ))}
      </section>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 lg:gap-6">
        {query.data.map((league) => (
          <LeagueCard key={league.league_id} {...league} />
        ))}
      </section>

      <Card className="border-dashed border-primary/25">
        <CardHeader className="flex flex-row items-center justify-between gap-4">
          <div>
            <CardTitle>Cross-League Exposure</CardTitle>
            <p className="mt-2 text-sm text-muted-foreground">
              Use the portfolio view to audit repeated bets, correlated NFL team
              clusters, and hedge opportunities across every league you track.
            </p>
          </div>
          <Link to="/portfolio" className={buttonClasses({ variant: "outline" })}>
            Inspect Portfolio
            <ArrowRight className="size-3.5" />
          </Link>
        </CardHeader>
      </Card>
    </div>
  )
}
