import { useMemo, useState } from "react"

import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { ChevronDown, ChevronUp } from "lucide-react"

import { leagueTradeHistoryOptions } from "@/api/queries"
import type {
  HistoricalAsset,
  HistoricalTradeEvaluationRow,
  HistoricalTradeParticipant,
  TradeEvaluation,
} from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

export const Route = createFileRoute("/league/$leagueId/trade-history")({
  component: LeagueTradeHistoryPage,
})

const DIMENSIONS: Array<[keyof TradeEvaluation, string]> = [
  ["market_fairness", "Market"],
  ["roster_fit", "Roster"],
  ["direction_fit", "Direction"],
  ["timing_quality", "Timing"],
  ["insulation_delta", "Insulation"],
  ["liquidity_delta", "Liquidity"],
  ["manager_exploit_quality", "Manager"],
]

function formatDate(value: string | null): string {
  if (!value) return "Unknown date"
  return new Date(value).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  })
}

function assetText(assets: HistoricalAsset[]): string {
  if (!assets.length) return "Nothing recorded"
  return assets.map((asset) => asset.label).join(", ")
}

function deltaText(value: number | null | undefined): string {
  if (value === null || value === undefined) return "--"
  return `${value > 0 ? "+" : ""}${value.toFixed(2)}`
}

function scoreTone(score: number): string {
  if (score >= 62) return "text-success"
  if (score <= 38) return "text-destructive"
  return "text-muted-foreground"
}

function participantBalance(participant: HistoricalTradeParticipant): number | null {
  return participant.current_replay?.trade_balance?.net_adjusted_delta ?? null
}

function participantSummary(participant: HistoricalTradeParticipant) {
  return (
    <div className="grid gap-3 rounded-xl border border-border/40 bg-card/35 p-4 md:grid-cols-2">
      <div>
        <p className="terminal-label text-muted-foreground">Sent</p>
        <p className="mt-2 text-sm">{assetText(participant.sends)}</p>
      </div>
      <div>
        <p className="terminal-label text-muted-foreground">Received</p>
        <p className="mt-2 text-sm">{assetText(participant.receives)}</p>
      </div>
    </div>
  )
}

function selectedParticipant(
  trade: HistoricalTradeEvaluationRow,
  selectedRosterId: number | null,
): HistoricalTradeParticipant | null {
  if (selectedRosterId === null) return null
  return (
    trade.participants.find((participant) => participant.roster_id === selectedRosterId) ?? null
  )
}

function EvaluationDetails({ evaluation }: { evaluation: TradeEvaluation }) {
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      {DIMENSIONS.map(([key, label]) => {
        const dimension = evaluation[key]
        return (
          <div key={key} className="rounded-lg border border-border/35 bg-background/35 p-3">
            <div className="flex items-center justify-between gap-2">
              <p className="terminal-label text-muted-foreground">{label}</p>
              <span className={`font-mono text-sm ${scoreTone(dimension.score)}`}>
                {dimension.score.toFixed(0)}
              </span>
            </div>
            <p className="mt-2 line-clamp-2 text-xs text-muted-foreground">{dimension.reasoning}</p>
          </div>
        )
      })}
    </div>
  )
}

function TradeRow({
  trade,
  expanded,
  onToggle,
  selectedRosterId,
}: {
  trade: HistoricalTradeEvaluationRow
  expanded: boolean
  onToggle: () => void
  selectedRosterId: number | null
}) {
  const focusedParticipant = selectedParticipant(trade, selectedRosterId)
  const rowDelta = focusedParticipant
    ? participantBalance(focusedParticipant)
    : trade.current_best_delta
  const rowReplayLabel = focusedParticipant
    ? focusedParticipant.roster_name
    : (trade.current_winner_name ?? "No clear winner")
  const detailParticipants = focusedParticipant ? [focusedParticipant] : trade.participants

  return (
    <div className="rounded-xl border border-border/45 bg-card/45">
      <button
        type="button"
        onClick={onToggle}
        aria-label={`Toggle trade ${trade.summary} from ${formatDate(trade.date)}`}
        className="grid w-full gap-3 p-4 text-left md:grid-cols-[1fr_auto_auto_auto] md:items-center"
      >
        <div>
          <p className="text-base font-semibold">{trade.summary}</p>
          <p className="mt-1 text-sm text-muted-foreground">
            {formatDate(trade.date)}
            {trade.week ? ` · Week ${trade.week}` : ""}
          </p>
        </div>
        <div>
          <p className="terminal-label text-muted-foreground">Current Replay</p>
          <p className="mt-1 text-sm font-semibold">{rowReplayLabel}</p>
        </div>
        <div>
          <p className="terminal-label text-muted-foreground">
            {focusedParticipant ? "Manager Delta" : "Best Delta"}
          </p>
          <p className="mt-1 font-mono text-sm">{deltaText(rowDelta)}</p>
        </div>
        <div className="flex items-center gap-2 md:justify-end">
          {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </div>
      </button>
      {expanded ? (
        <div className="space-y-4 border-t border-border/40 p-4">
          {detailParticipants.map((participant) => (
            <div key={participant.roster_id} className="space-y-3">
              {focusedParticipant ? null : (
                <p className="text-sm font-semibold">{participant.roster_name}</p>
              )}
              {participantSummary(participant)}
              <div className="flex flex-wrap items-center gap-3 text-sm">
                <Badge variant="outline">
                  Current delta {deltaText(participantBalance(participant))}
                </Badge>
              </div>
              {participant.current_replay ? (
                <EvaluationDetails evaluation={participant.current_replay} />
              ) : (
                <p className="text-sm text-muted-foreground">
                  {participant.current_replay_error ?? "Current replay unavailable."}
                </p>
              )}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  )
}

function LeagueTradeHistoryPage() {
  const { leagueId } = Route.useParams()
  const query = useQuery(leagueTradeHistoryOptions(leagueId))
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [managerFilter, setManagerFilter] = useState("all")

  const managers = useMemo(() => {
    const map = new Map<number, string>()
    for (const trade of query.data?.trades ?? []) {
      for (const participant of trade.participants) {
        map.set(participant.roster_id, participant.roster_name)
      }
    }
    return [...map.entries()].sort((a, b) => a[1].localeCompare(b[1]))
  }, [query.data?.trades])

  const trades = useMemo(() => {
    const allTrades = query.data?.trades ?? []
    if (managerFilter === "all") return allTrades
    const rosterId = Number(managerFilter)
    return allTrades.filter((trade) => trade.participant_roster_ids.includes(rosterId))
  }, [managerFilter, query.data?.trades])
  const selectedRosterId = managerFilter === "all" ? null : Number(managerFilter)

  if (query.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-72 w-full" />
      </div>
    )
  }

  if (query.isError || !query.data) {
    return <p className="text-sm text-muted-foreground">Trade history unavailable.</p>
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="terminal-label text-primary/85">League Trade Audit</p>
            <CardTitle className="mt-2 text-3xl">Past Trade Evaluations</CardTitle>
            <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
              Completed Sleeper trades replayed through the current app model. Selecting a manager
              frames every delta from that roster's perspective.
            </p>
          </div>
          <label className="space-y-2">
            <span className="terminal-label text-muted-foreground">Manager</span>
            <select
              value={managerFilter}
              onChange={(event) => setManagerFilter(event.target.value)}
              className="h-10 rounded-lg border border-border bg-background px-3 text-sm"
            >
              <option value="all">All managers</option>
              {managers.map(([rosterId, name]) => (
                <option key={rosterId} value={rosterId}>
                  {name}
                </option>
              ))}
            </select>
          </label>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-xl border border-border/40 bg-card/45 p-4">
              <p className="terminal-label text-muted-foreground">Trades</p>
              <p className="mt-2 font-mono text-2xl">{trades.length}</p>
            </div>
            <div className="rounded-xl border border-border/40 bg-card/45 p-4">
              <p className="terminal-label text-muted-foreground">Perspective</p>
              <p className="mt-2 text-sm text-muted-foreground">
                {managerFilter === "all"
                  ? "Rows show the best current replay delta across participants."
                  : "Rows show send, receive, and delta for the selected manager only."}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {trades.length ? (
        <div className="space-y-3">
          {trades.map((trade) => (
            <TradeRow
              key={trade.transaction_id}
              trade={trade}
              expanded={expandedId === trade.transaction_id}
              selectedRosterId={selectedRosterId}
              onToggle={() =>
                setExpandedId(expandedId === trade.transaction_id ? null : trade.transaction_id)
              }
            />
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="py-10">
            <p className="text-sm text-muted-foreground">No completed trades match this filter.</p>
            {managerFilter !== "all" ? (
              <Button className="mt-4" variant="outline" onClick={() => setManagerFilter("all")}>
                Clear filter
              </Button>
            ) : null}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
