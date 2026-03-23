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
  return (
    <Link
      to="/league/$leagueId/managers/$managerId"
      params={{ leagueId, managerId: String(summary.roster_id) }}
      className="block"
    >
      <Card className="hover:shadow-md transition-shadow">
        <CardContent className="space-y-2 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-semibold">{summary.manager_name}</p>
              {summary.direction_label ? (
                <Badge variant="secondary">
                  {formatModelLabel(summary.direction_label)}
                </Badge>
              ) : null}
            </div>
            <div
              className={`text-xs ${
                summary.low_confidence ? "opacity-75 text-muted-foreground" : "text-muted-foreground"
              }`}
            >
              Exploitability:{" "}
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
            </div>
          </div>
          <div className="text-xs text-muted-foreground">
            {summary.top_pitch_angle ? (
              <>
                <span className="font-medium text-primary">
                  {formatModelLabel(summary.top_pitch_angle.deal_archetype)}
                </span>{" "}
                {summary.top_pitch_angle.reasoning}
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
