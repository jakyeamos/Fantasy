import { useMemo, useState } from "react"

import { useQuery } from "@tanstack/react-query"
import { Link, createFileRoute } from "@tanstack/react-router"
import {
  ArrowRightLeft,
  Search,
  SlidersHorizontal,
  TrendingDown,
  TrendingUp,
  UserRound,
} from "lucide-react"

import { playerRankingsOptions } from "@/api/queries"
import type { PlayerRankingEntry } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { buttonClasses } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { useLeagueRosterSelection } from "@/lib/league-roster-selection"
import { cn } from "@/lib/utils"

export const Route = createFileRoute("/league/$leagueId/player-rankings")({
  component: PlayerRankingsPage,
})

type PositionFilter = "ALL" | "QB" | "RB" | "WR" | "TE"
type OwnershipFilter = "ALL" | "MINE" | "OTHER"

const positionFilters: PositionFilter[] = ["ALL", "QB", "RB", "WR", "TE"]

function formatValue(value: number | null): string {
  if (value === null) return "--"
  return Math.round(value * 100).toString()
}

function formatMarketValue(player: PlayerRankingEntry): string {
  if (player.fantasycalc_value !== null) {
    return Math.round(player.fantasycalc_value).toLocaleString()
  }
  return formatValue(player.lens_market)
}

function trendLabel(value: number | null): string {
  if (value === null) return "No trend"
  const rounded = Math.round(value)
  if (rounded > 0) return `+${rounded}`
  return String(rounded)
}

function playerTradeSearch(
  player: PlayerRankingEntry,
  leagueId: string,
  userRosterId?: number | null,
) {
  return {
    leagueId,
    userRosterId: userRosterId ?? undefined,
    counterpartyRosterId: player.is_user_roster ? undefined : player.roster_id,
    targetPlayerId: player.player_id,
    targetPlayerName: player.player_name,
    targetPlayerPosition: player.position,
    targetPlayerRosterId: player.roster_id,
  }
}

function PlayerRankingsPage() {
  const { leagueId, requestedRosterId, league } = useLeagueRosterSelection()
  const rankingsQuery = useQuery(playerRankingsOptions(leagueId, requestedRosterId))
  const [queryText, setQueryText] = useState("")
  const [position, setPosition] = useState<PositionFilter>("ALL")
  const [ownership, setOwnership] = useState<OwnershipFilter>("ALL")

  const rankings = rankingsQuery.data?.rankings ?? []
  const visibleRankings = useMemo(() => {
    const normalizedQuery = queryText.trim().toLowerCase()
    return rankings.filter((player) => {
      const matchesQuery =
        normalizedQuery.length === 0 ||
        player.player_name.toLowerCase().includes(normalizedQuery) ||
        player.owner_name.toLowerCase().includes(normalizedQuery)
      const matchesPosition = position === "ALL" || player.position === position
      const matchesOwnership =
        ownership === "ALL" ||
        (ownership === "MINE" ? player.is_user_roster : !player.is_user_roster)
      return matchesQuery && matchesPosition && matchesOwnership
    })
  }, [ownership, position, queryText, rankings])

  if (rankingsQuery.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  if (rankingsQuery.isError) {
    return (
      <p className="text-sm text-muted-foreground">
        Player rankings unavailable. Run intelligence for this league, then refresh.
      </p>
    )
  }

  const topOwnedCount = rankings.filter((player) => player.is_user_roster && player.rank <= 48).length
  const topTierCount = rankings.filter((player) => player.tier === 1).length
  const activeUserRosterId = requestedRosterId ?? league.user_roster_id

  return (
    <div className="space-y-6">
      <Card className="overflow-hidden">
        <CardHeader className="space-y-5">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div className="max-w-3xl space-y-3">
              <p className="terminal-label text-primary/85">Player Market Board</p>
              <CardTitle className="text-3xl">Dynasty rankings with live ownership</CardTitle>
              <p className="text-sm leading-6 text-muted-foreground">
                Ranked board for {league.league_name}. Values blend market lens, production,
                insulation, and roster-direction fit; each row shows who owns the player in this league.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-3 sm:min-w-[320px]">
              <div className="rounded-xl border border-border/50 bg-card/60 p-4">
                <p className="terminal-label text-muted-foreground">Top 48 Owned</p>
                <p className="mt-2 font-headline text-3xl font-extrabold">{topOwnedCount}</p>
              </div>
              <div className="rounded-xl border border-border/50 bg-card/60 p-4">
                <p className="terminal-label text-muted-foreground">Tier 1 Assets</p>
                <p className="mt-2 font-headline text-3xl font-extrabold">{topTierCount}</p>
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent className="border-t border-border/40 pt-5">
          <div className="grid gap-3 lg:grid-cols-[minmax(240px,1fr)_auto_auto] lg:items-center">
            <label className="relative block">
              <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <input
                className="h-11 w-full pl-10 pr-3 text-sm"
                placeholder="Search player or owner..."
                value={queryText}
                onChange={(event) => setQueryText(event.target.value)}
              />
            </label>
            <div className="flex flex-wrap gap-2">
              {positionFilters.map((item) => (
                <button
                  key={item}
                  type="button"
                  className={cn(
                    "rounded-lg border px-3 py-2 font-label text-xs font-bold uppercase tracking-[0.12em]",
                    position === item
                      ? "border-primary/50 bg-primary/14 text-primary"
                      : "border-border/60 bg-card/60 text-muted-foreground hover:text-foreground",
                  )}
                  onClick={() => setPosition(item)}
                >
                  {item}
                </button>
              ))}
            </div>
            <label className="flex items-center gap-2 text-sm text-muted-foreground">
              <SlidersHorizontal className="size-4" />
              <select
                className="h-11 px-3 text-sm"
                value={ownership}
                onChange={(event) => setOwnership(event.target.value as OwnershipFilter)}
              >
                <option value="ALL">All rosters</option>
                <option value="MINE">My roster</option>
                <option value="OTHER">Other rosters</option>
              </select>
            </label>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          <div className="hidden grid-cols-[72px_minmax(240px,1.4fr)_120px_minmax(220px,0.9fr)_120px_120px] gap-4 border-b border-border/50 px-5 py-3 text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground lg:grid">
            <span>Rank</span>
            <span>Player</span>
            <span>Value</span>
            <span>Owner</span>
            <span>Fit</span>
            <span>Trend</span>
          </div>
          <div className="divide-y divide-border/45">
            {visibleRankings.map((player) => (
              <div
                key={player.player_id}
                className={cn(
                  "grid gap-3 px-5 py-4 lg:grid-cols-[72px_minmax(240px,1.4fr)_120px_minmax(220px,0.9fr)_120px_120px] lg:items-center lg:gap-4",
                  player.is_user_roster ? "bg-primary/7" : "hover:bg-card/65",
                )}
              >
                <div className="flex items-center justify-between lg:block">
                  <span className="font-headline text-2xl font-extrabold tabular-nums">
                    {player.rank}
                  </span>
                  <Badge variant="outline">Tier {player.tier}</Badge>
                </div>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="truncate font-headline text-lg font-bold">{player.player_name}</p>
                    <Badge>{player.position}{player.position_rank}</Badge>
                    {player.team ? <Badge variant="outline">{player.team}</Badge> : null}
                    {player.age !== null ? <Badge variant="outline">Age {player.age}</Badge> : null}
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Score {(player.rank_score * 100).toFixed(1)}
                  </p>
                </div>
                <div>
                  <p className="terminal-label text-muted-foreground lg:hidden">Value</p>
                  <p className="font-headline text-xl font-extrabold tabular-nums">
                    {formatMarketValue(player)}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {player.fantasycalc_rank ? `FC rank ${player.fantasycalc_rank}` : "model lens"}
                  </p>
                </div>
                <div>
                  <p className="terminal-label text-muted-foreground lg:hidden">Owner</p>
                  <div className="flex flex-wrap items-center gap-2 lg:flex-nowrap">
                    <Link
                      to="/league/$leagueId/managers/$managerId"
                      params={{
                        leagueId,
                        managerId: String(player.roster_id),
                      }}
                      className="inline-flex min-w-0 items-center gap-1.5 font-label text-sm font-bold text-primary hover:text-foreground"
                    >
                      <UserRound className="size-3.5 shrink-0" />
                      <span className="truncate">{player.owner_name}</span>
                    </Link>
                    {player.is_user_roster ? <Badge variant="secondary">You</Badge> : null}
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <p className="text-xs text-muted-foreground">Roster {player.roster_id}</p>
                    <Link
                      to="/trades"
                      search={playerTradeSearch(player, leagueId, activeUserRosterId)}
                      className={buttonClasses({
                        variant: "outline",
                        size: "sm",
                        className: "h-7 px-2 text-[9px]",
                      })}
                    >
                      <ArrowRightLeft className="size-3" />
                      Evaluate
                    </Link>
                  </div>
                </div>
                <div>
                  <p className="terminal-label text-muted-foreground lg:hidden">Fit</p>
                  <p className="font-headline text-xl font-extrabold tabular-nums">
                    {formatValue(player.lens_direction)}
                  </p>
                  <p className="text-xs text-muted-foreground">direction</p>
                </div>
                <div>
                  <p className="terminal-label text-muted-foreground lg:hidden">Trend</p>
                  <div className="flex items-center gap-2">
                    {(player.trend_30day ?? 0) >= 0 ? (
                      <TrendingUp className="size-4 text-accent" />
                    ) : (
                      <TrendingDown className="size-4 text-destructive" />
                    )}
                    <span className="font-label text-sm font-bold">
                      {trendLabel(player.trend_30day)}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
          {visibleRankings.length === 0 ? (
            <p className="p-6 text-sm text-muted-foreground">
              No players match the current filters.
            </p>
          ) : null}
        </CardContent>
      </Card>
    </div>
  )
}
