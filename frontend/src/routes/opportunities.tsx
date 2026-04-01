import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"

import { opportunityFeedOptions } from "@/api/queries"
import { OpportunityCardList } from "@/components/opportunities/OpportunityCardList"

export const Route = createFileRoute("/opportunities")({
  component: OpportunityFeedPage,
})

function OpportunityFeedPage() {
  const query = useQuery(opportunityFeedOptions)

  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <p className="terminal-label text-muted-foreground">
          RANKED BY IMPACT - GAP MAGNITUDE x PROJECTION CONFIDENCE
        </p>
        <h2 className="font-headline text-4xl font-extrabold tracking-tight">
          Opportunity Feed
        </h2>
        <p className="max-w-3xl text-sm leading-6 text-muted-foreground">
          Scan one ordered list of dynasty buy, sell, and hold signals across
          every league you track, with trend confidence, market gaps, and
          similar-player context attached to each call.
        </p>
      </div>

      <OpportunityCardList
        items={query.data?.items ?? []}
        isLoading={query.isLoading}
        isError={query.isError}
      />
    </div>
  )
}
