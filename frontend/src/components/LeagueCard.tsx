import { Link } from "@tanstack/react-router"

import type { DashboardLeagueSummary } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"

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
              {props.direction_label}
            </p>
            <Badge variant={badgeVariant(props.confidence_band)}>
              {props.confidence_band}
            </Badge>
          </div>
        </CardHeader>
        <Separator />
        <CardContent className="space-y-3">
          <p className="text-sm leading-6">{props.primary_weakness}</p>
          {props.top_exploit_window ? (
            <p className="border-t border-border/60 pt-2 text-xs text-muted-foreground">
              {props.top_exploit_window}
            </p>
          ) : null}
          <p className="text-xs text-muted-foreground">
            {formatSnapshot(props.last_snapshot_at)}
          </p>
        </CardContent>
      </Card>
    </Link>
  )
}
