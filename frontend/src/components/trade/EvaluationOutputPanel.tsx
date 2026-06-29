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

function formatTradeValue(value: number): string {
  return value.toFixed(2)
}

function balanceLabel(score: number): string {
  if (score >= 62) return "Leans to you"
  if (score <= 38) return "Leans away"
  return "Balanced"
}

function TradeBalanceSeesaw({ evaluation }: { evaluation: TradeEvaluation }) {
  const balance = evaluation.trade_balance
  const score = balance?.fairness_score ?? evaluation.market_fairness.score
  const markerPosition = Math.max(4, Math.min(96, score))
  const sentRaw = balance?.sent_raw_value ?? 0
  const receivedRaw = balance?.received_raw_value ?? 0
  const sentAdjusted = balance?.sent_adjusted_value ?? 0
  const receivedAdjusted = balance?.received_adjusted_value ?? 0
  const note =
    balance?.package_quality_note ??
    "Adjusted value discounts loose add-ons so bulk bench pieces do not equal elite assets."

  return (
    <div className="rounded-xl border border-border/40 bg-card/45 p-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="terminal-label text-muted-foreground">Trade Balance</p>
          <p className="mt-1 text-lg font-semibold text-foreground">
            {balanceLabel(score)}
          </p>
        </div>
        <div className="text-right">
          <p className="terminal-label text-muted-foreground">App-Adjusted Fairness</p>
          <p className="font-mono text-xl text-foreground">{score.toFixed(0)}</p>
        </div>
      </div>
      <div className="mt-5">
        <div className="relative h-9">
          <div className="absolute left-0 right-0 top-4 h-2 rounded-full bg-muted">
            <div className="h-full rounded-full bg-gradient-to-r from-destructive/70 via-warning/70 to-success/80" />
          </div>
          <div className="absolute left-1/2 top-1 h-8 w-px -translate-x-1/2 bg-border" />
          <div
            className="absolute top-0 flex h-9 w-9 -translate-x-1/2 items-center justify-center rounded-full border border-primary/45 bg-background font-mono text-xs font-semibold text-primary transition-all"
            style={{ left: `${markerPosition}%` }}
          >
            {score.toFixed(0)}
          </div>
        </div>
        <div className="mt-1 flex justify-between text-xs text-muted-foreground">
          <span>You overpay</span>
          <span>Fair</span>
          <span>You gain value</span>
        </div>
      </div>
      {balance ? (
        <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
          <div className="rounded-lg border border-border/35 bg-background/35 p-3">
            <p className="terminal-label text-muted-foreground">You Send</p>
            <p className="mt-1 font-mono text-foreground">
              {formatTradeValue(sentAdjusted)} app adjusted
            </p>
            <p className="text-xs text-muted-foreground">
              {formatTradeValue(sentRaw)} consensus market value
            </p>
          </div>
          <div className="rounded-lg border border-border/35 bg-background/35 p-3">
            <p className="terminal-label text-muted-foreground">You Receive</p>
            <p className="mt-1 font-mono text-foreground">
              {formatTradeValue(receivedAdjusted)} app adjusted
            </p>
            <p className="text-xs text-muted-foreground">
              {formatTradeValue(receivedRaw)} consensus market value
            </p>
          </div>
        </div>
      ) : null}
      <p className="mt-3 text-sm text-muted-foreground">{note}</p>
    </div>
  )
}

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
        <TradeBalanceSeesaw evaluation={evaluation} />
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
