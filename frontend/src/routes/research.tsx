import { useQuery } from "@tanstack/react-query"
import { Link, createFileRoute } from "@tanstack/react-router"
import { ArrowRight, BookOpen, Search } from "lucide-react"

import { opportunityFeedOptions } from "@/api/queries"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { decisionCardFromOpportunity } from "@/v2/contracts/decision-card"
import { DecisionCard } from "@/v2/components/DecisionCard"
import { StatePanel } from "@/v2/components/StatePanel"

export const Route = createFileRoute("/research")({
  component: ResearchPage,
})

function ResearchPage() {
  const query = useQuery(opportunityFeedOptions)
  const cards = (query.data?.items ?? []).slice(0, 4).map(decisionCardFromOpportunity)

  return (
    <div className="space-y-8">
      <section className="grid gap-6 border-b border-border/45 pb-8 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-3">
          <p className="font-label text-label-xs font-bold uppercase tracking-label text-primary">
            Research desk
          </p>
          <h2 className="font-headline text-4xl font-extrabold tracking-tight">
            Evidence before universal rankings.
          </h2>
          <p className="max-w-3xl text-sm leading-6 text-muted-foreground">
            Market signals, rookie evidence, prospect models, and draft context are research inputs.
            The league and roster context decides whether a signal becomes a move.
          </p>
        </div>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-xl">
              <BookOpen className="size-4" /> Research lanes
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <Link
              to="/opportunities"
              className="flex items-center justify-between rounded-md border border-border/50 p-3 hover:border-primary/40"
            >
              <span>Market opportunities</span>
              <ArrowRight className="size-4" />
            </Link>
            <Link
              to="/draft-room"
              className="flex items-center justify-between rounded-md border border-border/50 p-3 hover:border-primary/40"
            >
              <span>Draft room</span>
              <ArrowRight className="size-4" />
            </Link>
          </CardContent>
        </Card>
      </section>

      <section className="space-y-4">
        <div className="flex items-center gap-2">
          <Search className="size-4 text-primary" />
          <h3 className="font-headline text-2xl font-extrabold">Current market evidence</h3>
        </div>
        {query.isLoading ? (
          <div className="grid gap-4 lg:grid-cols-2">
            {Array.from({ length: 2 }).map((_, index) => (
              <Skeleton key={index} className="h-64 w-full" />
            ))}
          </div>
        ) : null}
        {query.isError ? <StatePanel state="error" /> : null}
        {!query.isLoading && !query.isError && !cards.length ? (
          <StatePanel state={query.data?.status === "degraded" ? "degraded" : "empty"} />
        ) : null}
        {cards.length ? (
          <div className="grid gap-4 xl:grid-cols-2">
            {cards.map((card) => (
              <DecisionCard key={card.id} card={card} />
            ))}
          </div>
        ) : null}
      </section>
    </div>
  )
}
