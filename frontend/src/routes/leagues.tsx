import { useQuery } from "@tanstack/react-query"
import { Link, createFileRoute } from "@tanstack/react-router"
import { ArrowRight, ShieldAlert } from "lucide-react"

import { dashboardSummaryOptions } from "@/api/queries"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { StatePanel } from "@/v2/components/StatePanel"

export const Route = createFileRoute("/leagues")({
  component: LeaguesPage,
})

function LeaguesPage() {
  const query = useQuery(dashboardSummaryOptions)

  return (
    <div className="space-y-8">
      <section className="space-y-3 border-b border-border/45 pb-8">
        <p className="font-label text-label-xs font-bold uppercase tracking-label text-primary">
          League workspaces
        </p>
        <h2 className="font-headline text-4xl font-extrabold tracking-tight">
          Choose the roster that needs a decision.
        </h2>
        <p className="max-w-3xl text-sm leading-6 text-muted-foreground">
          Each workspace keeps direction, lineup gaps, roster hygiene, market,
          and league operations in one context. The global shell stays
          data-free; this destination owns the league read.
        </p>
      </section>

      {query.isLoading ? (
        <div className="grid gap-4 md:grid-cols-2">
          {Array.from({ length: 3 }).map((_, index) => (
            <Skeleton key={index} className="h-52 w-full" />
          ))}
        </div>
      ) : query.isError ? (
        <StatePanel state="error" />
      ) : !query.data?.length ? (
        <StatePanel
          state="empty"
          title="No leagues connected"
          body="Add or ingest a Sleeper league before opening a decision workspace."
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {query.data.map((league) => (
            <Card key={league.league_id} className="flex flex-col">
              <CardHeader className="flex-1">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-label text-label-xs font-bold uppercase tracking-label text-muted-foreground">
                      League briefing
                    </p>
                    <CardTitle className="mt-2 text-2xl">
                      {league.league_name}
                    </CardTitle>
                  </div>
                  <Badge
                    variant={
                      league.confidence_band === "High"
                        ? "secondary"
                        : "outline"
                    }
                  >
                    {league.confidence_band} read
                  </Badge>
                </div>
                <p className="mt-4 text-sm leading-6 text-muted-foreground">
                  {league.summary_signal}
                </p>
              </CardHeader>
              <CardContent className="space-y-3 border-t border-border/40 pt-4">
                <div className="flex items-start gap-2 text-sm">
                  <ShieldAlert className="mt-0.5 size-4 shrink-0 text-primary" />
                  <span>{league.primary_weakness}</span>
                </div>
                <Link
                  to="/league/$leagueId"
                  params={{ leagueId: league.league_id }}
                  search={
                    league.user_roster_id
                      ? { rosterId: league.user_roster_id }
                      : undefined
                  }
                  className="inline-flex min-h-10 w-full items-center justify-center gap-2 rounded-md border border-primary/35 bg-primary px-4 py-2 font-label text-label-sm font-bold uppercase tracking-label text-primary-foreground hover:bg-primary/90"
                >
                  Open briefing <ArrowRight className="size-4" />
                </Link>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
