import type { OrphanIntake } from "@/api/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

type OrphanIntakeStatusCardProps = {
  intake: OrphanIntake
}

const summaryByLabel: Record<OrphanIntake["composite_label"], string> = {
  Distressed:
    "Immediate churn and liquidation should come before any long-view patience.",
  Rebuilder:
    "This roster has enough bones to keep, but it needs insulation and cleaner timelines.",
  Balanced:
    "The team is salvageable without a teardown, but every move should stay value-aware.",
  "Ready to Compete":
    "This orphan can push sooner than expected if you avoid unnecessary reshaping.",
}

export function OrphanIntakeStatusCard({
  intake,
}: OrphanIntakeStatusCardProps) {
  return (
    <Card>
      <CardHeader>
        <p className="terminal-label text-primary/85">Orphan Intake</p>
        <CardTitle className="mt-2 text-display-card font-extrabold tracking-tight">
          {intake.composite_label}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <p className="font-mono text-sm">
          Composite {intake.composite_score.toFixed(1)}
        </p>
        <p className="text-sm leading-6 text-muted-foreground">
          {summaryByLabel[intake.composite_label]}
        </p>
      </CardContent>
    </Card>
  )
}
