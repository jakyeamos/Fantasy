import { useQuery } from "@tanstack/react-query"

import { lineupScoreOptions } from "@/api/queries"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

type LineupStrengthCardProps = {
  leagueId: string
  rosterId: number
}

export function LineupStrengthCard({ leagueId, rosterId }: LineupStrengthCardProps) {
  const { data, isLoading, isError } = useQuery(lineupScoreOptions(leagueId, rosterId))

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full min-h-[40px]" />
        ))}
      </div>
    )
  }

  if (isError) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground">Starter scores unavailable.</p>
        </CardContent>
      </Card>
    )
  }

  if (!data || data.slot_scores.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Lineup strength</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No lineup data yet. Run a roster ingest to see position-by-position starter strength.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Lineup strength</CardTitle>
        <p className="text-sm text-muted-foreground">
          Starter score vs. replacement level by slot.
        </p>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          {data.slot_scores.map((row) => (
            <div
              key={`${row.position}-${row.player_id}`}
              className="flex min-h-[40px] flex-col gap-1 rounded-lg border border-border/50 bg-card/40 p-3"
            >
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline">{row.position}</Badge>
                <span className="text-sm font-medium">{row.player_name}</span>
              </div>
              <div className="flex flex-wrap items-baseline gap-2">
                <span className="font-mono text-sm">{row.starter_value.toFixed(2)}</span>
                <span className="text-xs text-muted-foreground">
                  vs repl {row.replacement_level.toFixed(2)}
                </span>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
