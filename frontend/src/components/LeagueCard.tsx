import { Link } from "@tanstack/react-router"

import type { DashboardLeagueSummary } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { formatModelLabel } from "@/lib/utils"

function badgeVariant(confidenceBand: DashboardLeagueSummary["confidence_band"]) {
  if (confidenceBand === "High") return "default"
  if (confidenceBand === "Medium") return "secondary"
  return "outline"
}

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
  const leadLabel = props.top_exploit_window ? "Live market" : "Top edge"
  const leadCopy = props.top_exploit_window ?? props.summary_signal

  return (
    <Link
      to="/league/$leagueId"
      params={{ leagueId: props.league_id }}
      className="group block h-full"
    >
      <Card className="h-full min-h-[180px] cursor-pointer overflow-hidden border-primary/10 bg-card/90 hover:shadow-md transition-shadow">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            {props.league_name}
          </CardTitle>
          <div className="flex items-center gap-2">
            <p className="text-xl font-semibold tracking-tight">
              {formatModelLabel(props.direction_label)}
            </p>
            <Badge variant={badgeVariant(props.confidence_band)}>
              {props.confidence_band}
            </Badge>
          </div>
        </CardHeader>
        <Separator />
        <CardContent className="space-y-3">
          <div className="space-y-1">
            <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
              {leadLabel}
            </p>
            <p className="text-sm leading-6">{leadCopy}</p>
          </div>
          {props.top_exploit_window ? (
            <div className="border-t border-border/60 pt-2">
              <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                Top edge
              </p>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">
                {props.summary_signal}
              </p>
            </div>
          ) : null}
          <p className="text-xs text-muted-foreground">
            {formatSnapshot(props.last_snapshot_at)}
          </p>
        </CardContent>
      </Card>
    </Link>
  )
}
