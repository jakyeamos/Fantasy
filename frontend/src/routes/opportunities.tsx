import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"

import { opportunityFeedOptions } from "@/api/queries"
import { OpportunityCardList } from "@/components/opportunities/OpportunityCardList"
import { Skeleton } from "@/components/ui/skeleton"

export const Route = createFileRoute("/opportunities")({
  component: OpportunityFeedPage,
})

function OpportunityFeedPage() {
  const query = useQuery(opportunityFeedOptions)
  const items = query.data?.items ?? []
  const topSignal = items[0] ?? null
  const updatedAt = query.data?.computed_at
    ? new Intl.DateTimeFormat("en", {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      }).format(new Date(query.data.computed_at))
    : "Pending"

  return (
    <div className="space-y-8">
      <section className="grid gap-5 border-b border-border/45 pb-8 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-3">
          <p className="terminal-label text-primary/85">
            Ranked by impact - gap magnitude x projection confidence
          </p>
          <h2 className="font-headline text-4xl font-extrabold">
            Opportunity Feed
          </h2>
          <p className="max-w-3xl text-sm leading-6 text-muted-foreground">
            Scan one ordered list of dynasty buy, sell, and hold signals across
            every league you track, with trend confidence, market gaps, and
            similar-player context attached to each call.
          </p>
        </div>

        <div className="grid grid-cols-3 overflow-hidden rounded-xl border border-border/60 bg-card/60">
          <div className="border-r border-border/45 p-4">
            <p className="terminal-label text-muted-foreground">Signals</p>
            {query.isLoading ? (
              <Skeleton className="mt-3 h-7 w-12" />
            ) : (
              <p className="mt-2 font-headline text-2xl font-extrabold">
                {query.data?.total ?? items.length}
              </p>
            )}
          </div>
          <div className="border-r border-border/45 p-4">
            <p className="terminal-label text-muted-foreground">Top impact</p>
            {query.isLoading ? (
              <Skeleton className="mt-3 h-7 w-14" />
            ) : (
              <p className="mt-2 font-headline text-2xl font-extrabold">
                {topSignal ? Math.round(topSignal.impact_score) : "-"}
              </p>
            )}
          </div>
          <div className="p-4">
            <p className="terminal-label text-muted-foreground">Updated</p>
            {query.isLoading ? (
              <Skeleton className="mt-3 h-5 w-20" />
            ) : (
              <p className="mt-2 text-sm font-bold text-foreground">{updatedAt}</p>
            )}
          </div>
        </div>
      </section>

      <OpportunityCardList
        items={items}
        isLoading={query.isLoading}
        isError={query.isError}
      />
    </div>
  )
}
