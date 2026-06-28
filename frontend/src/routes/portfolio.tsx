import { useMemo } from "react"

import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { AlertTriangle, Briefcase, Radar, ShieldAlert } from "lucide-react"

import {
  dashboardSummaryOptions,
  portfolioExposureOptions,
  portfolioHealthOptions,
} from "@/api/queries"
import { CorrelatedRiskSection } from "@/components/CorrelatedRiskSection"
import { ExposureMatrix } from "@/components/ExposureMatrix"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"

export const Route = createFileRoute("/portfolio")({
  validateSearch: (search: Record<string, unknown>) => ({
    playerId: typeof search.playerId === "string" ? search.playerId : undefined,
  }),
  component: PortfolioPage,
})

function formatLongDate(value: string | null) {
  if (!value) {
    return "Not yet recalibrated."
  }
  return `Last recalibrated: ${new Date(value).toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  })}`
}

function PortfolioPage() {
  const search = Route.useSearch()
  const exposureQuery = useQuery(portfolioExposureOptions())
  const healthQuery = useQuery(portfolioHealthOptions())
  const dashboardQuery = useQuery(dashboardSummaryOptions)

  const leagueColumns = useMemo(() => {
    const leagueNameById = new Map(
      (dashboardQuery.data ?? []).map((league) => [league.league_id, league.league_name]),
    )
    const ids =
      dashboardQuery.data?.map((league) => league.league_id) ??
      Array.from(
        new Set((exposureQuery.data?.exposure ?? []).flatMap((row) => row.owned_in_leagues)),
      )

    return ids
      .map((leagueId) => ({
        leagueId,
        leagueName: leagueNameById.get(leagueId) ?? leagueId,
      }))
      .sort((a, b) => a.leagueName.localeCompare(b.leagueName))
  }, [dashboardQuery.data, exposureQuery.data?.exposure])
  const exposureRows = exposureQuery.data?.exposure ?? []
  const correlatedRisk = exposureQuery.data?.correlated_risk ?? []
  const concentratedRows = exposureRows.filter((row) => row.league_count >= 3).length

  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <p className="terminal-label text-muted-foreground">
          Cross-League View
        </p>
        <h2 className="font-headline text-4xl font-extrabold tracking-tight">
          Portfolio
        </h2>
        <p className="max-w-3xl text-sm leading-6 text-muted-foreground">
          Track repeated bets across leagues, spot concentrated exposure, and
          surface correlated team risk before a single NFL outcome hits multiple
          rosters at once.
        </p>
      </div>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[
          {
            label: "Tracked Leagues",
            value: String(leagueColumns.length),
            helper: "Mapped to portfolio",
            icon: Briefcase,
            tone: "text-primary",
          },
          {
            label: "Exposed Players",
            value: String(exposureRows.length),
            helper: "Owned in multiple leagues",
            icon: Radar,
            tone: "text-accent",
          },
          {
            label: "High Concentration",
            value: String(concentratedRows),
            helper: "3+ leagues on one player",
            icon: ShieldAlert,
            tone: "text-destructive",
          },
          {
            label: "Correlated Clusters",
            value: String(correlatedRisk.length),
            helper: "NFL team overlap alerts",
            icon: AlertTriangle,
            tone: "text-primary",
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

      <Card>
        <CardHeader>
          <CardTitle>Player Exposure</CardTitle>
          <p className="mt-2 text-sm text-muted-foreground">
            Audit ownership overlap by league, then review hedge notes and team-level
            correlation underneath the matrix.
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <ExposureMatrix
            rows={exposureRows}
            leagueColumns={leagueColumns}
            isLoading={exposureQuery.isLoading}
            isError={exposureQuery.isError}
            highlightedPlayerId={search.playerId}
          />
          <Separator className="my-4" />
          <CorrelatedRiskSection
            rows={correlatedRisk}
            isLoading={exposureQuery.isLoading}
            isError={exposureQuery.isError}
          />
        </CardContent>
      </Card>

      <div className="flex items-center justify-end border-t pt-4 text-xs text-muted-foreground">
        {healthQuery.isLoading ? (
          <Skeleton className="h-4 w-48 rounded" />
        ) : (
          <span>{formatLongDate(healthQuery.data?.last_recalibrated_at ?? null)}</span>
        )}
      </div>
    </div>
  )
}
