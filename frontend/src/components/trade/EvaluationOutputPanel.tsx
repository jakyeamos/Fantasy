import type { PickValue, TradeAsset, TradeEvaluation } from "@/api/types"
import { PickValueSummaryRow } from "@/components/picks/PickValueSummaryRow"
import { RecommendationCardList } from "@/components/recommendations/RecommendationCardList"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
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
  leagueId,
  userSends,
  userReceives,
  pickValuesByKey,
  counterpartyName,
  rosterNamesById,
  onOpenReroutes,
  onOpenPackage,
}: {
  evaluation: TradeEvaluation
  leagueId: string
  userSends: TradeAsset[]
  userReceives: TradeAsset[]
  pickValuesByKey: Map<string, PickValue>
  counterpartyName?: string | null
  rosterNamesById?: Map<number, string>
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
        <p className="mt-2 text-sm text-muted-foreground">
          Seven-dimension trade scoring, strategic framing, and pick context.
        </p>
      </CardHeader>
      <CardContent className="space-y-6">
        <StrategicDistinctionBanner distinction={evaluation.strategic_distinction} />
        <div className="rounded-xl border border-border/40 bg-card/45 p-4">
          {DIMENSIONS.map(([key, label]) => (
            <DimensionScoreRow
              key={String(key)}
              label={label}
              score={evaluation[key] as never}
            />
          ))}
        </div>
        {evaluation.third_party_evaluations?.length ? (
          <div className="rounded-xl border border-border/40 bg-card/45 p-4">
            <p className="terminal-label text-muted-foreground">Third-Party Legs</p>
            <div className="mt-3 space-y-3">
              {evaluation.third_party_evaluations.map((sidecar) => (
                <div key={sidecar.roster_id} className="space-y-2">
                  <DimensionScoreRow
                    label={`${rosterNamesById?.get(sidecar.roster_id) ?? `Roster ${sidecar.roster_id}`} Market Fairness`}
                    score={sidecar.market_fairness}
                  />
                  <p className="text-xs text-muted-foreground">
                    Sends {sidecar.sent_market_value.toFixed(2)} market value, receives{" "}
                    {sidecar.received_market_value.toFixed(2)}.
                  </p>
                </div>
              ))}
            </div>
          </div>
        ) : null}
        {pickSummaryRows.length ? (
          <div className="space-y-3">
            <p className="terminal-label text-muted-foreground">Pick Context</p>
            {pickSummaryRows.map((row, index) => (
              <div key={`${row.side}-${index}`} className="space-y-2">
                <p className="terminal-label text-muted-foreground">
                  {row.side}
                </p>
                <PickValueSummaryRow
                  pickValue={row.value}
                  leagueId={leagueId}
                  managerName={counterpartyName}
                />
              </div>
            ))}
          </div>
        ) : null}
        {evaluation.recommendation_cards && evaluation.recommendation_cards.length > 0 ? (
          <>
            <Separator className="my-4" />
            <div className="space-y-3">
              <p className="terminal-label text-muted-foreground">Recommendations</p>
              <RecommendationCardList cards={evaluation.recommendation_cards} />
            </div>
          </>
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
