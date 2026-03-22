import type { TradeEvaluation } from "@/api/types"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { DimensionScoreRow } from "@/components/trade/DimensionScoreRow"
import { StrategicDistinctionBanner } from "@/components/trade/StrategicDistinctionBanner"

const DIMENSIONS: Array<[keyof TradeEvaluation, string]> = [
  ["market_fairness", "Market Fairness"],
  ["roster_fit", "Roster Fit"],
  ["direction_fit", "Direction Fit"],
  ["timing_quality", "Timing Quality"],
  ["insulation_delta", "Insulation Gain/Loss"],
  ["liquidity_delta", "Liquidity Gain/Loss"],
  ["manager_exploit_quality", "Manager Exploit Quality"],
]

export function EvaluationOutputPanel({
  evaluation,
  onOpenReroutes,
  onOpenPackage,
}: {
  evaluation: TradeEvaluation
  onOpenReroutes: () => void
  onOpenPackage: () => void
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Evaluation</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <StrategicDistinctionBanner distinction={evaluation.strategic_distinction} />
        <div>
          {DIMENSIONS.map(([key, label]) => (
            <DimensionScoreRow
              key={String(key)}
              label={label}
              score={evaluation[key] as never}
            />
          ))}
        </div>
        <div className="flex flex-wrap gap-3">
          <Button onClick={onOpenReroutes}>See reroutes</Button>
          <Button variant="outline" onClick={onOpenPackage}>
            Build Package
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
