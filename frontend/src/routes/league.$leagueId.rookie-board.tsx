import { useMemo, useState } from "react"

import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"

import { rookieBoardOptions } from "@/api/queries"
import { TierGroup } from "@/components/rookie/TierGroup"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

export const Route = createFileRoute("/league/$leagueId/rookie-board")({
  component: RookieBoardPage,
})

function RookieBoardPage() {
  const { leagueId } = Route.useParams()
  const [slot, setSlot] = useState("1.01")
  const query = useQuery(rookieBoardOptions(leagueId))

  const slotOptions = useMemo(
    () =>
      Array.from({ length: 24 }, (_, index) => {
        const pick = index + 1
        const round = Math.floor(index / 12) + 1
        const pickInRound = (index % 12) + 1
        return {
          value: `${round}.${String(pickInRound).padStart(2, "0")}`,
          label: `${round}.${String(pickInRound).padStart(2, "0")}`,
        }
      }),
    [],
  )

  if (query.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-12 w-56" />
        <Skeleton className="h-48 w-full" />
      </div>
    )
  }

  if (query.isError || !query.data) {
    return (
      <p className="text-sm text-muted-foreground">
        Rookie board unavailable. Try refreshing or recomputing on the backend.
      </p>
    )
  }

  return (
    <div className="space-y-8">
      <Card>
        <CardHeader className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="terminal-label text-primary/85">Draft intelligence</p>
            <CardTitle className="mt-2 text-3xl">Rookie Board</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">
              {query.data.league_format} · Class strength {query.data.class_strength_signal.toFixed(2)}
            </p>
          </div>
          <label className="space-y-2">
            <span className="terminal-label text-muted-foreground">
              Highlight availability at slot
            </span>
            <select
              value={slot}
              onChange={(event) => setSlot(event.target.value)}
              className="h-11 rounded-lg border border-border bg-card px-3 text-sm"
            >
              {slotOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </CardHeader>
      </Card>

      {query.data.tiers.length ? (
        query.data.tiers.map((tier) => (
          <TierGroup key={tier.tier_number} tier={tier} selectedSlot={slot} />
        ))
      ) : (
        <Card className="border-dashed border-border/45">
          <CardContent className="p-5">
            <p className="text-sm text-muted-foreground">
              No rookie board candidates are available for this league yet.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
