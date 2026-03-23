import type { PickValue, TradeAsset, TradeEvaluation } from "@/api/types"
import { PickValueSummaryRow } from "@/components/picks/PickValueSummaryRow"
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
  userSends,
  userReceives,
  pickValuesByKey,
  counterpartyName,
  onOpenReroutes,
  onOpenPackage,
}: {
  evaluation: TradeEvaluation
  userSends: TradeAsset[]
  userReceives: TradeAsset[]
  pickValuesByKey: Map<string, PickValue>
  counterpartyName?: string | null
  onOpenReroutes: () => void
  onOpenPackage: () => void
}) {
  const pickSummaryRows = [
    ...userSends
      .filter((asset) => asset.asset_type === "pick")
      .map((asset) => ({
        side: "You Send",
        value:
          pickValuesByKey.get(
            `${asset.pick_owner_roster_id ?? 0}:${asset.pick_year ?? 0}:${asset.pick_round ?? 0}`,
          ) ?? null,
      })),
    ...userReceives
      .filter((asset) => asset.asset_type === "pick")
      .map((asset) => ({
        side: "You Receive",
        value:
          pickValuesByKey.get(
            `${asset.pick_owner_roster_id ?? 0}:${asset.pick_year ?? 0}:${asset.pick_round ?? 0}`,
          ) ?? null,
      })),
  ].filter((row): row is { side: string; value: PickValue } => row.value !== null)

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
        {pickSummaryRows.length ? (
          <div className="space-y-3">
            <p className="text-sm font-semibold">Pick Context</p>
            {pickSummaryRows.map((row, index) => (
              <div key={`${row.side}-${index}`} className="space-y-2">
                <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">
                  {row.side}
                </p>
                <PickValueSummaryRow
                  pickValue={row.value}
                  managerName={counterpartyName}
                />
              </div>
            ))}
          </div>
        ) : null}
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
