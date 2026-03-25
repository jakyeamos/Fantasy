import type { ManagerProfile } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { formatModelLabel } from "@/lib/utils"

function label(type: string | null) {
  if (!type) return "No clear type"
  return formatModelLabel(type)
}

export function DossierOverviewTab({
  profile,
}: {
  profile: ManagerProfile
}) {
  const positionalNeeds = profile.roster_summary?.positional_needs ?? []

  return (
    <div className="space-y-4">
      {profile.low_confidence ? (
        <div className="rounded-xl border border-destructive/25 bg-destructive/10 p-4 text-destructive">
          <p className="terminal-label">Low confidence</p>
          <p className="mt-2 text-sm">
            Based on {profile.evidence_count} trades (minimum 10 for reliable profiling). Treat all conclusions with skepticism.
          </p>
        </div>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Exploitation Type</CardTitle>
          <p className="mt-2 text-sm text-muted-foreground">
            Primary patterns inferred from how this manager has historically traded.
          </p>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <Badge>{label(profile.exploitation_primary)}</Badge>
            {profile.exploitation_secondary ? (
              <Badge variant="secondary">{label(profile.exploitation_secondary)}</Badge>
            ) : null}
          </div>
          {Object.entries(profile.exploitation_evidence).map(([key, value]) => (
            <p
              key={key}
              className="rounded-lg border border-border/35 bg-card/45 px-3 py-2 text-sm text-muted-foreground"
            >
              {value}
            </p>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Roster Summary</CardTitle>
          <p className="mt-2 text-sm text-muted-foreground">
            Direction, needs, and trade output from this roster’s current profile.
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Direction: {formatModelLabel(profile.direction_label) ?? "Unknown"}
          </p>
          <Separator />
          <div className="space-y-2">
            <p className="text-sm font-medium">Positional Needs</p>
            {positionalNeeds.length === 0 ? (
              <p className="text-sm text-muted-foreground">No positional needs surfaced.</p>
            ) : (
              <ul className="space-y-2 text-sm text-muted-foreground">
                {positionalNeeds.map((position) => (
                  <li
                    key={position}
                    className="rounded-lg border border-border/35 bg-card/45 px-3 py-2"
                  >
                    {position}
                  </li>
                ))}
              </ul>
            )}
          </div>
          <Separator />
          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-lg border border-border/35 bg-card/45 p-4">
              <p className="text-xl font-semibold">
                {profile.aggregate_trade_stats.total_trades}
              </p>
              <p className="text-xs text-muted-foreground">Total Trades</p>
            </div>
            <div className="rounded-lg border border-border/35 bg-card/45 p-4">
              <p className="text-xl font-semibold">
                {(profile.aggregate_trade_stats.win_rate * 100).toFixed(0)}%
              </p>
              <p className="text-xs text-muted-foreground">Win Rate</p>
            </div>
            <div className="rounded-lg border border-border/35 bg-card/45 p-4">
              <p className="text-xl font-semibold">
                {profile.aggregate_trade_stats.avg_delta.toFixed(2)}
              </p>
              <p className="text-xs text-muted-foreground">Avg Value Delta</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
