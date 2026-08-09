import type { OrphanIntake } from "@/api/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

type AgeCurveRiskPanelProps = {
  intake: OrphanIntake
}

export function AgeCurveRiskPanel({ intake }: AgeCurveRiskPanelProps) {
  return (
    <Card>
      <CardHeader>
        <p className="terminal-label text-muted-foreground">Age Curve Risk</p>
        <CardTitle>{intake.age_curve.label}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center justify-between rounded-lg border border-border/50 bg-card/35 px-4 py-3">
          <span className="text-sm font-semibold">Age curve score</span>
          <span className="font-mono text-sm">
            {intake.age_curve.score.toFixed(1)}
          </span>
        </div>
        <p className="text-sm leading-6 text-muted-foreground">
          {intake.age_curve.summary}
        </p>
      </CardContent>
    </Card>
  )
}
