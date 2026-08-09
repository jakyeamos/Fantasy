import { Link } from "@tanstack/react-router"
import { ArrowRight, Shield, Skull, Trophy, Zap } from "lucide-react"

import type { DashboardLeagueSummary } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { directionReadBadgeVariant, formatModelLabel } from "@/lib/utils"

function formatSnapshot(snapshot: string | null) {
  if (!snapshot) return "No snapshot yet"
  const deltaMs = Date.now() - Date.parse(snapshot)
  const minutes = Math.floor(deltaMs / 60_000)
  if (minutes < 1) return "Last snapshot: just now"
  if (minutes < 60) return `Last snapshot: ${minutes} minutes ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `Last snapshot: ${hours} hours ago`
  return `Last snapshot: ${new Date(snapshot).toLocaleDateString()}`
}

export function LeagueCard(props: DashboardLeagueSummary) {
  const leadLabel = props.top_exploit_window ? "Live Market" : "Top Edge"
  const leadCopy = props.top_exploit_window ?? props.summary_signal
  const DirectionIcon = props.direction_label.includes("contender")
    ? Trophy
    : props.direction_label.includes("rebuild") ||
        props.direction_label.includes("punt")
      ? Skull
      : props.direction_label.includes("retool")
        ? Shield
        : Zap

  return (
    <Link
      to="/league/$leagueId"
      params={{ leagueId: props.league_id }}
      className="group block h-full"
    >
      <Card className="h-full min-h-[250px] cursor-pointer overflow-hidden border-border/50 bg-card/75 transition-transform duration-200 group-hover:-translate-y-1 group-hover:border-primary/30">
        <CardHeader className="space-y-4 pb-2">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="flex size-10 items-center justify-center rounded-lg border border-border/40 bg-card/60 text-primary">
                <DirectionIcon className="size-4" />
              </div>
              <div>
                <p className="terminal-label text-muted-foreground">
                  League Briefing
                </p>
                <CardTitle className="mt-2 text-xl">
                  {props.league_name}
                </CardTitle>
              </div>
            </div>
            <Badge variant={directionReadBadgeVariant(props.direction_read)}>
              {props.direction_read}
            </Badge>
          </div>
          <div className="flex items-center justify-between gap-3 border-t border-border/40 pt-4">
            <div>
              <p className="terminal-label text-muted-foreground">Direction</p>
              <p className="mt-2 text-xl font-semibold tracking-tight text-foreground">
                {formatModelLabel(props.direction_label)}
              </p>
              {props.direction_note ? (
                <p className="mt-2 max-w-xs text-xs leading-5 text-muted-foreground">
                  {props.direction_note}
                </p>
              ) : null}
            </div>
            <ArrowRight className="size-4 text-muted-foreground transition-colors group-hover:text-primary" />
          </div>
        </CardHeader>
        <Separator />
        <CardContent className="space-y-4">
          <div className="space-y-1">
            <p className="terminal-label text-muted-foreground">{leadLabel}</p>
            <p className="text-sm leading-6 text-foreground">{leadCopy}</p>
          </div>
          {props.top_exploit_window ? (
            <div className="rounded-lg border border-primary/20 bg-primary/10 p-3">
              <p className="terminal-label text-primary/85">Top Edge</p>
              <p className="mt-2 text-xs leading-5 text-muted-foreground">
                {props.summary_signal}
              </p>
            </div>
          ) : null}
          <div className="flex items-center justify-between gap-3 border-t border-border/40 pt-4">
            <p className="font-mono text-label-sm uppercase tracking-label text-muted-foreground">
              {formatSnapshot(props.last_snapshot_at)}
            </p>
            <span className="terminal-label text-primary/75">
              Full Analysis
            </span>
          </div>
        </CardContent>
      </Card>
    </Link>
  )
}
