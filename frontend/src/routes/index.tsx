import { useMemo } from "react"

import { useQuery } from "@tanstack/react-query"
import { Link, createFileRoute } from "@tanstack/react-router"
import { ArrowRight, Database, RefreshCw, Sparkles } from "lucide-react"

import {
  dashboardSummaryOptions,
  decisionCardsOptions,
  todayBriefOptions,
} from "@/api/queries"
import { MorningBriefPanel } from "@/components/intelligence/MorningBriefPanel"
import { Button, buttonClasses } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { DecisionCard } from "@/v2/components/DecisionCard"
import { StatePanel } from "@/v2/components/StatePanel"

export const Route = createFileRoute("/")({
  component: TodayPage,
})

function TodayPage() {
  const decisionQuery = useQuery(decisionCardsOptions)
  const summaryQuery = useQuery(dashboardSummaryOptions)
  const briefQuery = useQuery(todayBriefOptions)
  const cards = useMemo(
    () => decisionQuery.data?.cards.slice(0, 6) ?? [],
    [decisionQuery.data?.cards],
  )

  return (
    <div className="space-y-8">
      <section className="grid gap-6 border-b border-border/45 pb-8 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-4">
          <p className="font-label text-label-xs font-bold uppercase tracking-label text-primary">
            Prepared front-office briefing
          </p>
          <h2 className="max-w-3xl font-headline text-4xl font-extrabold tracking-tight sm:text-5xl">
            Decide what matters today.
          </h2>
          <p className="max-w-2xl text-base leading-7 text-muted-foreground">
            Verified local league evidence becomes a small set of reversible
            next moves. Every card keeps its timing, confidence, freshness,
            downside, and evidence attached.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link to="/leagues" className={buttonClasses({ size: "lg" })}>
              Open leagues <ArrowRight className="size-4" />
            </Link>
            <Link
              to="/operations"
              className={buttonClasses({ variant: "outline", size: "lg" })}
            >
              Check data health <Database className="size-4" />
            </Link>
          </div>
        </div>

        <Card className="border-primary/25 bg-primary/5">
          <CardHeader>
            <div className="flex items-center gap-2 text-primary">
              <Sparkles className="size-4" />
              <p className="font-label text-label-xs font-bold uppercase tracking-label">
                Desk status
              </p>
            </div>
            <CardTitle className="text-2xl">Local evidence loop</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex items-center justify-between gap-3">
              <span className="text-muted-foreground">Connected leagues</span>
              <span className="font-mono font-semibold">
                {summaryQuery.isLoading
                  ? "—"
                  : (summaryQuery.data?.length ?? 0)}
              </span>
            </div>
            <div className="flex items-center justify-between gap-3">
              <span className="text-muted-foreground">Prepared decisions</span>
              <span className="font-mono font-semibold">
                {decisionQuery.isLoading ? "—" : cards.length}
              </span>
            </div>
            <div className="flex items-center justify-between gap-3">
              <span className="text-muted-foreground">Morning brief</span>
              <span className="font-mono font-semibold capitalize">
                {briefQuery.isLoading
                  ? "loading"
                  : (briefQuery.data?.status ?? "not run")}
              </span>
            </div>
            <p className="border-t border-border/40 pt-3 text-xs leading-5 text-muted-foreground">
              Nothing here submits a trade, waiver, lineup, or league action.
            </p>
          </CardContent>
        </Card>
      </section>

      {decisionQuery.isLoading ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-64 w-full" />
          ))}
        </div>
      ) : decisionQuery.isError ? (
        <StatePanel state="error" />
      ) : !cards.length ? (
        <StatePanel state="empty" />
      ) : (
        <section aria-labelledby="decision-list-title" className="space-y-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="font-label text-label-xs font-bold uppercase tracking-label text-primary">
                Next moves
              </p>
              <h3
                id="decision-list-title"
                className="mt-2 font-headline text-2xl font-extrabold"
              >
                Ranked by roster consequence
              </h3>
            </div>
            <span className="text-sm text-muted-foreground">
              {decisionQuery.data?.total ?? cards.length} total signals
            </span>
          </div>
          <div className="grid gap-4 xl:grid-cols-2">
            {cards.map((card) => (
              <DecisionCard key={card.id} card={card} />
            ))}
          </div>
        </section>
      )}

      <section className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
        <MorningBriefPanel />
        <Card className="h-fit">
          <CardHeader>
            <CardTitle className="text-xl">Refresh boundary</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm leading-6 text-muted-foreground">
            <p>
              Source refreshes, URL analysis, and review decisions write only to
              the local evidence store. They never transmit a fantasy action.
            </p>
            <Link
              to="/operations"
              className={buttonClasses({
                variant: "outline",
                className: "w-full",
              })}
            >
              <RefreshCw className="size-4" />
              Open operations
            </Link>
          </CardContent>
        </Card>
      </section>
    </div>
  )
}
