import { useMemo, useState } from "react"

import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"

import { prospectModelOutputsOptions, rookieBoardOptions } from "@/api/queries"
import type { ProspectModelOutput, RookiePlayer } from "@/api/types"
import { RookiePlayerCard } from "@/components/rookie/RookiePlayerCard"
import { CalendarStateBadge } from "@/components/context/CalendarStateBadge"
import { FreshnessWarningBar } from "@/components/context/FreshnessWarningBar"
import { TierGroup } from "@/components/rookie/TierGroup"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

export const Route = createFileRoute("/league/$leagueId/rookie-board")({
  component: RookieBoardPage,
})

function RookieBoardPage() {
  const { leagueId } = Route.useParams()
  const [slot, setSlot] = useState("1.01")
  const [sortBy, setSortBy] = useState<"tier" | "adp_divergence" | "hit_rate">("tier")
  const query = useQuery(rookieBoardOptions(leagueId))
  const prospectQuery = useQuery(prospectModelOutputsOptions(leagueId))

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

  const prospectMap = useMemo(
    () => new Map((prospectQuery.data ?? []).map((item) => [item.player_id, item])),
    [prospectQuery.data],
  )

  const flatPlayers = useMemo(
    () => query.data?.rookie_board.tiers.flatMap((tier) => tier.players) ?? [],
    [query.data],
  )

  const sortedPlayers = useMemo(() => {
    if (sortBy === "tier") {
      return flatPlayers
    }
    const players = [...flatPlayers]
    players.sort((left, right) => {
      const leftOutput = prospectMap.get(left.player_id)
      const rightOutput = prospectMap.get(right.player_id)
      if (sortBy === "adp_divergence") {
        return (rightOutput?.overvalue_magnitude ?? -1) - (leftOutput?.overvalue_magnitude ?? -1)
      }
      return hitRateWeight(rightOutput) - hitRateWeight(leftOutput)
    })
    return players
  }, [flatPlayers, prospectMap, sortBy])

  if (query.isLoading) {
    return (
      <div
        data-mac-control-id="fantasy.league.rookie-board-loading"
        data-task-state="rookie_board_loading"
        className="space-y-4"
        role="status"
        aria-label="Loading rookie board"
        aria-busy="true"
      >
        <Skeleton className="h-12 w-56" />
        <Skeleton className="h-48 w-full" />
      </div>
    )
  }

  if (query.isError || !query.data) {
    return (
      <p
        data-mac-control-id="fantasy.league.rookie-board-error"
        data-task-state="rookie_board_failed"
        className="text-sm text-muted-foreground"
        role="alert"
      >
        Rookie board unavailable. Try refreshing or recomputing on the backend.
      </p>
    )
  }

  return (
    <div
      data-mac-control-id="fantasy.league.rookie-board-workspace"
      data-task-state={sortedPlayers.length === 0 ? "rookie_board_empty" : "rookie_board_ready"}
      data-player-count={sortedPlayers.length}
      data-selected-slot={slot}
      data-sort={sortBy}
      className="space-y-8"
      role="region"
      aria-label="Rookie board"
    >
      <Card>
        <CardHeader className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="terminal-label text-primary/85">Draft intelligence</p>
            <CardTitle className="mt-2 text-3xl">Rookie Board</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">
              {query.data.rookie_board.league_format} · Class strength{" "}
              {query.data.rookie_board.class_strength_signal.toFixed(2)}
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
          <label className="space-y-2">
            <span className="terminal-label text-muted-foreground">Sort board</span>
            <select
              value={sortBy}
              onChange={(event) =>
                setSortBy(event.target.value as "tier" | "adp_divergence" | "hit_rate")
              }
              className="h-11 rounded-lg border border-border bg-card px-3 text-sm"
            >
              <option value="tier">Tier</option>
              <option value="adp_divergence">ADP divergence</option>
              <option value="hit_rate">Hit rate</option>
            </select>
          </label>
        </CardHeader>
        <CardContent className="space-y-2 pt-0">
          <CalendarStateBadge state={query.data.recommendation_context.calendar_state} />
          {query.data.recommendation_context.calendar_note ? (
            <p className="text-xs text-muted-foreground">
              {query.data.recommendation_context.calendar_note}
            </p>
          ) : null}
          <FreshnessWarningBar tags={query.data.recommendation_context.freshness_tags} />
        </CardContent>
      </Card>

      {query.data.rookie_board.tiers.length ? (
        sortBy === "tier" ? (
          query.data.rookie_board.tiers.map((tier) => (
            <TierGroup
              key={tier.tier_number}
              tier={tier}
              selectedSlot={slot}
              prospectMap={prospectMap}
              isModelLoading={prospectQuery.isLoading}
            />
          ))
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {sortedPlayers.map((player) => (
              <RookiePlayerCard
                key={player.player_id}
                player={player}
                modelOutput={prospectMap.get(player.player_id) ?? null}
                isModelLoading={prospectQuery.isLoading}
                selectedSlot={slot}
                isAvailableAtSlot={
                  slot ? (player.available_probability_by_slot[slot] ?? 0) >= 0.5 : false
                }
              />
            ))}
          </div>
        )
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

function hitRateWeight(output?: ProspectModelOutput | null) {
  if (!output || output.low_confidence) {
    return -1
  }
  if (output.hit_rate_bucket === "High hit rate") {
    return 3
  }
  if (output.hit_rate_bucket === "Moderate hit rate") {
    return 2
  }
  return 1
}
