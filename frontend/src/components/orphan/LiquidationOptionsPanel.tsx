import type { ActionPlan, OrphanIntake } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

type LiquidationOptionsPanelProps = {
  intake: OrphanIntake
  plan: ActionPlan | null
}

export function LiquidationOptionsPanel({ intake, plan }: LiquidationOptionsPanelProps) {
  const tradeItems = plan?.items.filter((item) => item.category === "trade") ?? []

  return (
    <Card>
      <CardHeader>
        <p className="terminal-label text-muted-foreground">Liquidation Options</p>
        <CardTitle>{intake.liquidation_options.label}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm leading-6 text-muted-foreground">
          {intake.liquidation_options.summary}
        </p>
        {tradeItems.length ? (
          tradeItems.map((item) => (
            <div
              key={`${item.headline}-${item.priority_rank}`}
              className="rounded-lg border border-border/50 bg-card/35 px-4 py-3"
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-semibold">{item.headline}</span>
                <Badge variant="outline">Sell Now</Badge>
              </div>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">{item.rationale}</p>
            </div>
          ))
        ) : (
          <p className="text-sm leading-6 text-muted-foreground">
            No liquidation paths have been surfaced yet.
          </p>
        )}
      </CardContent>
    </Card>
  )
}
