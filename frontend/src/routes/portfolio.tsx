import { useMemo } from "react"

import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"

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

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <div className="space-y-1">
        <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
          Cross-League View
        </p>
        <h2 className="text-[20px] font-semibold">Portfolio</h2>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Player Exposure</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <ExposureMatrix
            rows={exposureQuery.data?.exposure ?? []}
            leagueColumns={leagueColumns}
            isLoading={exposureQuery.isLoading}
            isError={exposureQuery.isError}
          />
          <Separator className="my-4" />
          <CorrelatedRiskSection
            rows={exposureQuery.data?.correlated_risk ?? []}
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
