import type { ManagerProfile } from "@/api/types"
import { RookiePickMarketCard } from "@/components/RookiePickMarketCard"
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
          <CardTitle>How to Trade With {profile.manager_name ?? "This Manager"}</CardTitle>
          <p className="mt-2 text-sm text-muted-foreground">
            Specific trade guidance based on behavioral patterns in their trade history.
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          {profile.recent_urgency_state ? (
            <div className="flex items-center gap-2">
              <p className="terminal-label">Urgency State</p>
              <Badge
                variant={
                  profile.recent_urgency_state === "panic_mode"
                    ? "default"
                    : profile.recent_urgency_state === "declining_window"
                      ? "default"
                      : profile.recent_urgency_state === "building_urgency"
                        ? "secondary"
                        : "outline"
                }
              >
                {formatModelLabel(profile.recent_urgency_state)}
              </Badge>
            </div>
          ) : null}

          {profile.likely_motivations_now ? (
            <div className="rounded-lg border border-border/35 bg-card/45 px-3 py-2 text-sm text-muted-foreground">
              {profile.likely_motivations_now}
            </div>
          ) : null}

          <Separator />

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <p className="terminal-label mb-2">Best Asset to Send</p>
              {profile.best_asset_to_send ? (
                <p className="text-sm text-muted-foreground">
                  {profile.best_asset_to_send}
                </p>
              ) : (
                <p className="text-sm text-muted-foreground">
                  {profile.low_confidence
                    ? "Insufficient trade evidence - see pitch angles for approach."
                    : "No dominant asset preference detected."}
                </p>
              )}
            </div>
            <div>
              <p className="terminal-label mb-2">Best Asset to Target</p>
              {profile.best_asset_to_target ? (
                <p className="text-sm text-muted-foreground">
                  {profile.best_asset_to_target}
                </p>
              ) : (
                <p className="text-sm text-muted-foreground">
                  {profile.low_confidence
                    ? "Insufficient trade evidence - check roster needs below."
                    : "No clear target identified from trade history."}
                </p>
              )}
            </div>
          </div>

          {!profile.low_confidence ? (
            <>
              <Separator />
              <p className="terminal-label">Behavioral Vectors</p>
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                {[
                  {
                    label: "Veteran Appetite",
                    value: profile.veteran_appetite ?? 0,
                  },
                  {
                    label: "Rookie Fever",
                    value: profile.rookie_fever_index ?? 0,
                  },
                  {
                    label: "Value Rigidity",
                    value: profile.value_rigidity ?? 0,
                  },
                  {
                    label: "Reroute Susceptibility",
                    value: profile.reroute_susceptibility ?? 0,
                  },
                ].map(({ label: vectorLabel, value }) => (
                  <div
                    key={vectorLabel}
                    className="rounded-lg border border-border/35 bg-card/45 p-3"
                  >
                    <p className="text-lg font-semibold">
                      {(value * 100).toFixed(0)}
                    </p>
                    <p className="text-xs text-muted-foreground">{vectorLabel}</p>
                  </div>
                ))}
              </div>
            </>
          ) : null}
        </CardContent>
      </Card>

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
              <Badge variant="secondary">
                {label(profile.exploitation_secondary)}
              </Badge>
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

      <RookiePickMarketCard
        positionalTendency={profile.positional_tendency ?? {}}
        dominantArchetype={profile.dominant_archetype ?? null}
        pickPremiumScore={profile.pick_premium_score ?? null}
      />
    </div>
  )
}
