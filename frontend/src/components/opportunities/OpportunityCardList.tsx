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
}: {
  items: OpportunityFeedItem[]
  isLoading: boolean
  isError: boolean
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
        <CardContent className="p-6">
          <p className="text-sm text-muted-foreground">
            Opportunity feed could not be loaded. Check your data connection and
            try refreshing.
          </p>
        </CardContent>
      </Card>
    )
  }

  if (items.length === 0) {
    return (
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
    )
  }

  return (
    <div className="space-y-3">
      {items.map((item, index) => (
        <OpportunityCard key={item.player_id} item={item} rank={index + 1} />
      ))}
    </div>
  )
}
