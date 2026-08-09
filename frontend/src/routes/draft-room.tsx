import { useEffect, useState } from "react"

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

  useEffect(() => {
    setLeagueId(search.leagueId)
    setPickSlot(search.pickSlot)
  }, [search.leagueId, search.pickSlot])

  return (
    <div className="space-y-8">
      <Card>
        <CardHeader>
          <p className="terminal-label text-primary/85">Live pick guidance</p>
          <CardTitle className="mt-2 text-3xl">Draft Room</CardTitle>
          <p className="mt-2 text-sm text-muted-foreground">
            Load a league and pick slot to get a use-versus-trade verdict plus
            the best player available in abstract.
          </p>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_auto]">
          <label className="space-y-2">
            <span className="terminal-label text-muted-foreground">
              League ID
            </span>
            <input
              value={leagueId}
              onChange={(event) => setLeagueId(event.target.value)}
              className="h-11 w-full rounded-lg border border-border bg-card px-3 text-sm"
            />
          </label>
          <label className="space-y-2">
            <span className="terminal-label text-muted-foreground">
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
              <CardTitle>Ready-State Advice</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3 text-sm leading-6 text-muted-foreground md:grid-cols-3">
              <p>
                <span className="font-semibold text-foreground">
                  Selected pick:
                </span>{" "}
                {query.data.pick_slot_display}
              </p>
              <p>
                <span className="font-semibold text-foreground">
                  Trade-back line:
                </span>{" "}
                {query.data.trade_back_line ??
                  query.data.trade_verdict.reasoning}
              </p>
              <p>
                <span className="font-semibold text-foreground">
                  Expected tier:
                </span>{" "}
                {query.data.expected_available_tier ??
                  "Use board tier at the slot."}
              </p>
              {query.data.avoid_at_cost?.length ? (
                <p className="md:col-span-3">
                  <span className="font-semibold text-foreground">
                    Avoid at cost:
                  </span>{" "}
                  {query.data.avoid_at_cost.join(", ")}
                </p>
              ) : null}
            </CardContent>
          </Card>

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
