import type { OpportunityFeedItem } from "@/api/types"
import { OpportunityCard } from "@/components/opportunities/OpportunityCard"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

function OpportunityCardSkeleton() {
  return (
    <Card>
      <CardContent className="space-y-3 p-5">
        <div className="flex items-center gap-3">
          <Skeleton className="size-11 rounded-lg" />
          <div className="space-y-2">
            <Skeleton className="h-5 w-40" />
            <Skeleton className="h-3 w-28" />
          </div>
        </div>
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-10 w-full" />
      </CardContent>
    </Card>
  )
}

export function OpportunityCardList({
  items,
  isLoading,
  isError,
  isTimeout,
  isDegraded,
  degradedReason,
}: {
  items: OpportunityFeedItem[]
  isLoading: boolean
  isError: boolean
  isTimeout: boolean
  isDegraded: boolean
  degradedReason: string | null
}) {
  if (isLoading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 5 }).map((_, index) => (
          <OpportunityCardSkeleton key={index} />
        ))}
      </div>
    )
  }

  if (isError) {
    return (
      <Card>
        <CardContent className="space-y-2 p-6">
          <p className="font-headline text-2xl font-bold tracking-tight">
            {isTimeout
              ? "Opportunity Feed Timed Out"
              : "Opportunity Feed Unavailable"}
          </p>
          <p className="text-sm text-muted-foreground">
            {isTimeout
              ? "The local opportunity pass did not finish within the request budget."
              : "Opportunity feed could not be loaded. Check your data connection and try refreshing."}
          </p>
        </CardContent>
      </Card>
    )
  }

  const degradedBanner = isDegraded ? (
    <Card>
      <CardContent className="space-y-2 p-5">
        <p className="font-headline text-xl font-bold tracking-tight">
          Opportunity Feed Degraded
        </p>
        <p className="text-sm text-muted-foreground">
          {degradedReason ?? "Partial opportunity data is available."}
        </p>
      </CardContent>
    </Card>
  ) : null

  if (items.length === 0) {
    return (
      <div className="space-y-3">
        {degradedBanner}
        <Card>
          <CardContent className="space-y-2 p-6">
            <p className="font-headline text-2xl font-bold tracking-tight">
              No Opportunities Available
            </p>
            <p className="text-sm text-muted-foreground">
              Ingest fresh roster and valuation data to surface buy, sell, and
              hold signals across your leagues.
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {degradedBanner}
      {items.map((item, index) => (
        <OpportunityCard key={item.player_id} item={item} rank={index + 1} />
      ))}
    </div>
  )
}
