import { useQuery } from "@tanstack/react-query"
import { AlertTriangle, ArrowRightLeft } from "lucide-react"

import { weeklyEdgeOptions } from "@/api/queries"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

function confidenceVariant(confidence: "HIGH" | "MEDIUM" | "LOW") {
  if (confidence === "HIGH") return "default"
  if (confidence === "MEDIUM") return "secondary"
  return "outline"
}

export function WeeklyEdgePanel({
  leagueId,
  rosterId,
  focus,
  startPlayerId,
  sitPlayerId,
  position,
}: {
  leagueId: string
  rosterId: number
  focus?: "weekly"
  startPlayerId?: string
  sitPlayerId?: string
  position?: string
}) {
  const query = useQuery(weeklyEdgeOptions(leagueId, rosterId))

  if (query.isLoading) {
    return (
      <Card>
        <CardContent className="space-y-3 p-5">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-16 w-full" />
        </CardContent>
      </Card>
    )
  }

  if (query.isError || !query.data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Weekly Edge</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Weekly edge data is unavailable for this roster.
          </p>
        </CardContent>
      </Card>
    )
  }

  const topStartSit = query.data.start_sit[0] ?? null
  const topGap = query.data.lineup_gaps[0] ?? null
  const topStartSignal = topStartSit
    ? query.data.player_signals.find(
        (signal) => signal.player_id === topStartSit.start_player_id,
      )
    : null
  const startSitFocused =
    focus === "weekly" &&
    topStartSit !== null &&
    topStartSit.start_player_id === startPlayerId &&
    topStartSit.sit_player_id === sitPlayerId
  const gapFocused =
    focus === "weekly" &&
    topGap !== null &&
    position !== undefined &&
    topGap.position.toLowerCase() === position.toLowerCase()
  const isFocused = startSitFocused || gapFocused

  return (
    <Card id="weekly-edge" className={cn("border-primary/25", isFocused && "ring-2 ring-primary/55")}>
      <CardHeader className="space-y-2">
        <p className="terminal-label text-primary/85">Weekly Edge</p>
        <CardTitle>Start, sit, and lineup pressure</CardTitle>
        {isFocused ? (
          <div className="rounded border border-primary/30 bg-primary/10 px-3 py-2 text-xs text-primary">
            Opened from a command-center action. The matching decision is highlighted below.
          </div>
        ) : null}
        {query.data.stale_domains.length ? (
          <div className="flex flex-wrap items-center gap-2 rounded border border-orange-400/30 bg-orange-400/10 px-3 py-2 text-xs text-orange-300">
            <AlertTriangle className="size-3.5" />
            Refresh {query.data.stale_domains.join(", ")} before treating this as final.
          </div>
        ) : null}
      </CardHeader>
      <CardContent className="grid gap-4 lg:grid-cols-2">
        {topStartSit ? (
          <div
            className={cn(
              "rounded-lg border border-border/45 bg-card/45 p-4",
              startSitFocused && "border-primary/60 bg-primary/10",
            )}
          >
            <div className="flex flex-wrap items-center gap-2">
              <ArrowRightLeft className="size-4 text-primary" />
              <Badge variant={confidenceVariant(topStartSit.confidence)}>
                {topStartSit.confidence}
              </Badge>
              <span className="terminal-label text-muted-foreground">
                Start/Sit
              </span>
            </div>
            <p className="mt-3 text-sm font-semibold">
              {topStartSit.recommendation}
            </p>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              {topStartSit.why_now}
            </p>
            {topStartSit.stale_domains.length ? null : topStartSignal?.usage_note ? (
              <p className="mt-2 text-xs text-muted-foreground">
                {topStartSignal.usage_note}
              </p>
            ) : null}
            {topStartSignal?.role_note ? (
              <p className="mt-2 text-xs text-muted-foreground">
                {topStartSignal.role_note}
              </p>
            ) : null}
            {topStartSignal?.bye_week_warning ? (
              <p className="mt-2 text-xs text-orange-300">
                {topStartSignal.bye_week_warning}
              </p>
            ) : null}
            <p className="mt-2 text-xs text-muted-foreground">
              Wrong if: {topStartSit.risk_if_wrong}
            </p>
          </div>
        ) : (
          <div className="rounded-lg border border-border/45 bg-card/45 p-4">
            <p className="terminal-label text-muted-foreground">Start/Sit</p>
            <p className="mt-3 text-sm text-muted-foreground">
              No bench player currently clears the swap threshold from recent
              production and opportunity.
            </p>
          </div>
        )}

        {topGap ? (
          <div
            className={cn(
              "rounded-lg border border-border/45 bg-card/45 p-4",
              gapFocused && "border-primary/60 bg-primary/10",
            )}
          >
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={confidenceVariant(topGap.confidence)}>
                {topGap.confidence}
              </Badge>
              <span className="terminal-label text-muted-foreground">
                Lineup Gap
              </span>
            </div>
            <p className="mt-3 text-sm font-semibold">
              {topGap.recommended_action}
            </p>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              {topGap.why_now}
            </p>
          </div>
        ) : (
          <div className="rounded-lg border border-border/45 bg-card/45 p-4">
            <p className="terminal-label text-muted-foreground">Lineup Gap</p>
            <p className="mt-3 text-sm text-muted-foreground">
              No cached starter slot is currently below the playoff or title target.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
