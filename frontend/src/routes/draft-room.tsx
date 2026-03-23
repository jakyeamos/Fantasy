import { useState } from "react"

import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"

import { draftRoomOptions } from "@/api/queries"
import { VerdictBanner } from "@/components/draft-room/VerdictBanner"
import { TendencyWarningList } from "@/components/draft-room/TendencyWarningList"
import { RookiePlayerCard } from "@/components/rookie/RookiePlayerCard"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

export const Route = createFileRoute("/draft-room")({
  validateSearch: (search: Record<string, unknown>) => ({
    leagueId: typeof search.leagueId === "string" ? search.leagueId : "",
    pickSlot:
      typeof search.pickSlot === "number"
        ? search.pickSlot
        : typeof search.pickSlot === "string"
          ? Number(search.pickSlot) || 1
          : 1,
  }),
  component: DraftRoomPage,
})

function DraftRoomPage() {
  const search = Route.useSearch()
  const navigate = Route.useNavigate()
  const [leagueId, setLeagueId] = useState(search.leagueId)
  const [pickSlot, setPickSlot] = useState(search.pickSlot)
  const query = useQuery(draftRoomOptions(leagueId, pickSlot))

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Draft Room</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_auto]">
          <label className="space-y-2">
            <span className="text-xs uppercase tracking-[0.16em] text-muted-foreground">
              League ID
            </span>
            <input
              value={leagueId}
              onChange={(event) => setLeagueId(event.target.value)}
              className="h-11 w-full rounded-lg border border-border bg-card px-3 text-sm"
            />
          </label>
          <label className="space-y-2">
            <span className="text-xs uppercase tracking-[0.16em] text-muted-foreground">
              Pick Slot
            </span>
            <input
              type="number"
              min={1}
              value={pickSlot}
              onChange={(event) => setPickSlot(Number(event.target.value) || 1)}
              className="h-11 w-full rounded-lg border border-border bg-card px-3 text-sm"
            />
          </label>
          <div className="flex items-end">
            <Button
              variant="outline"
              onClick={() => {
                void navigate({
                  search: { leagueId, pickSlot },
                })
              }}
            >
              Load
            </Button>
          </div>
        </CardContent>
      </Card>

      {query.isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
      ) : null}

      {query.isError ? (
        <p className="text-sm text-muted-foreground">
          Draft room unavailable. Check the league ID and backend.
        </p>
      ) : null}

      {query.data ? (
        <div className="space-y-6">
          <VerdictBanner verdict={query.data.trade_verdict} />

          <Card>
            <CardHeader>
              <CardTitle>Best In Abstract</CardTitle>
            </CardHeader>
            <CardContent>
              {query.data.best_in_abstract ? (
                <RookiePlayerCard player={query.data.best_in_abstract} />
              ) : (
                <p className="text-sm text-muted-foreground">
                  No premium prospect stands out for this slot.
                </p>
              )}
            </CardContent>
          </Card>

          <TendencyWarningList warnings={query.data.tendency_warnings} />
        </div>
      ) : null}
    </div>
  )
}
