import type { ManagerProfile } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { formatModelLabel } from "@/lib/utils"

export function DossierOverviewTab({ profile }: { profile: ManagerProfile }) {
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>How to Trade With {profile.manager_name ?? "This Manager"}</CardTitle>
          <p className="mt-2 text-sm text-muted-foreground">
            Specific trade guidance based on behavioral patterns in their trade history.
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-2 rounded-lg border border-border/40 bg-card/45 px-3 py-2 text-sm text-muted-foreground">
            <span className="font-semibold text-foreground">Evidence:</span>
            <Badge variant={profile.low_confidence ? "outline" : "secondary"}>
              {profile.low_confidence ? "Weak sample" : "Actionable sample"}
            </Badge>
            <span>{profile.evidence_count} trades</span>
            <span>Exploitability {profile.exploitability_score.toFixed(0)}</span>
          </div>

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
                <p className="text-sm text-muted-foreground">{profile.best_asset_to_send}</p>
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
                <p className="text-sm text-muted-foreground">{profile.best_asset_to_target}</p>
              ) : (
                <p className="text-sm text-muted-foreground">
                  {profile.low_confidence
                    ? "Insufficient trade evidence - check roster needs below."
                    : "No clear target identified from trade history."}
                </p>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
