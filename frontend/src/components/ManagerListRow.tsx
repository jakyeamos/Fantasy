import { Link } from "@tanstack/react-router"

import type { ManagerSummary } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { formatModelLabel } from "@/lib/utils"

export function ManagerListRow({
  leagueId,
  summary,
}: {
  leagueId: string
  summary: ManagerSummary
}) {
  const confidenceLabel = summary.low_confidence
    ? "Weak sample"
    : summary.evidence_count >= 5
      ? "High evidence"
      : "Medium evidence"

  return (
    <Link
      to="/league/$leagueId/managers/$managerId"
      params={{ leagueId, managerId: String(summary.roster_id) }}
      className="block"
    >
      <Card className="border-border/45 transition-transform duration-200 hover:-translate-y-1 hover:border-primary/25">
        <CardContent className="space-y-3 p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <div>
                <p className="terminal-label text-muted-foreground">Manager</p>
                <p className="mt-2 text-sm font-semibold">{summary.manager_name}</p>
              </div>
              {summary.direction_label ? (
                <Badge variant="secondary">
                  {formatModelLabel(summary.direction_label)}
                </Badge>
              ) : null}
              {summary.pick_premium_score !== null &&
              summary.pick_premium_score !== undefined ? (
                <Badge variant="default">Picks Buyer</Badge>
              ) : null}
            </div>
            <div className="rounded-lg border px-3 py-2 text-xs text-muted-foreground">
              <span className="terminal-label">Exploitability</span>{" "}
              <span
                className={
                  summary.low_confidence
                    ? "font-semibold text-muted-foreground"
                    : "font-semibold text-primary"
                }
              >
                {summary.exploitability_score.toFixed(0)}
              </span>{" "}
              | {summary.evidence_count} trades
              <Badge
                className="ml-2"
                variant={summary.low_confidence ? "outline" : "secondary"}
              >
                {confidenceLabel}
              </Badge>
            </div>
          </div>
          <div className="rounded-lg border border-border/35 bg-card/45 p-3 text-xs text-muted-foreground">
            {summary.top_pitch_angle ? (
              <>
                <span className="font-label text-label-xs text-primary">
                  Best pitch now: {formatModelLabel(summary.top_pitch_angle.deal_archetype)}
                </span>{" "}
                {summary.low_confidence
                  ? "Sample is thin, so use this only as a starting hypothesis."
                  : summary.top_pitch_angle.reasoning}
              </>
            ) : (
              "Insufficient trade history for pitch angle."
            )}
          </div>
        </CardContent>
      </Card>
    </Link>
  )
}
