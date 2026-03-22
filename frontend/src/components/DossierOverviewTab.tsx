import type { ManagerProfile } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"

function label(type: string | null) {
  if (!type) return "No clear type"
  return type.replaceAll("_", " ")
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
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-amber-900">
          <p className="text-xs font-semibold tracking-[0.18em]">LOW CONFIDENCE</p>
          <p className="mt-2 text-sm">
            Based on {profile.evidence_count} trades (minimum 10 for reliable profiling). Treat all conclusions with skepticism.
          </p>
        </div>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Exploitation Type</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <Badge>{label(profile.exploitation_primary)}</Badge>
            {profile.exploitation_secondary ? (
              <Badge variant="secondary">{label(profile.exploitation_secondary)}</Badge>
            ) : null}
          </div>
          {Object.entries(profile.exploitation_evidence).map(([key, value]) => (
            <p key={key} className="text-sm text-muted-foreground">
              {value}
            </p>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Roster Summary</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Direction: {profile.direction_label ?? "Unknown"}
          </p>
          <Separator />
          <div className="space-y-2">
            <p className="text-sm font-medium">Positional Needs</p>
            {positionalNeeds.length === 0 ? (
              <p className="text-sm text-muted-foreground">No positional needs surfaced.</p>
            ) : (
              <ul className="space-y-1 text-sm text-muted-foreground">
                {positionalNeeds.map((position) => (
                  <li key={position}>{position}</li>
                ))}
              </ul>
            )}
          </div>
          <Separator />
          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <p className="text-xl font-semibold">
                {profile.aggregate_trade_stats.total_trades}
              </p>
              <p className="text-xs text-muted-foreground">Total Trades</p>
            </div>
            <div>
              <p className="text-xl font-semibold">
                {(profile.aggregate_trade_stats.win_rate * 100).toFixed(0)}%
              </p>
              <p className="text-xs text-muted-foreground">Win Rate</p>
            </div>
            <div>
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
