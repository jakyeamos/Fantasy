import { useQuery } from "@tanstack/react-query"

import { slotOccupancyOptions } from "@/api/queries"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

type TaxiIRSlotSummaryProps = {
  leagueId: string
  rosterId: number
}

export function TaxiIRSlotSummary({ leagueId, rosterId }: TaxiIRSlotSummaryProps) {
  const { data, isLoading, isError } = useQuery(slotOccupancyOptions(leagueId, rosterId))

  if (isLoading) {
    return <Skeleton className="h-8 w-full max-w-md" />
  }

  if (isError || !data) {
    return (
      <p className="text-sm text-muted-foreground">
        Taxi and IR slots could not be determined — check league config.
      </p>
    )
  }

  const { taxi_used, taxi_total, ir_used, ir_total } = data

  if (taxi_total === 0) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Slots</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1 font-mono text-sm">
          <p>Taxi: not configured</p>
          <p>
            IR: {ir_used}/{ir_total} occupied
          </p>
        </CardContent>
      </Card>
    )
  }

  const taxiFree = taxi_total - taxi_used
  const spotLabel = taxiFree === 1 ? "spot" : "spots"

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Slots</CardTitle>
      </CardHeader>
      <CardContent className="space-y-1 font-mono text-sm">
        <p>
          Taxi: {taxi_used}/{taxi_total} occupied — {taxiFree} {spotLabel} available
        </p>
        <p>
          IR: {ir_used}/{ir_total} occupied
        </p>
      </CardContent>
    </Card>
  )
}
