import type { RecommendationCard as RecommendationCardType } from "@/api/types"
import { ConfidenceBadge } from "@/components/recommendations/ConfidenceBadge"
import { MarketGapPanel } from "@/components/recommendations/MarketGapPanel"
import { PlayerContextFlagRow } from "@/components/recommendations/PlayerContextFlagRow"
import { PriorityRankPill } from "@/components/recommendations/PriorityRankPill"
import { SupportingFactorRow } from "@/components/recommendations/SupportingFactorRow"
import { TrendBadge } from "@/components/opportunities/TrendBadge"
import { Button, buttonClasses } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"

function isLikelyContextFlag(factorName: string) {
  return [
    "availability",
    "depth chart pressure",
    "role expansion",
    "role compression",
    "team context",
    "age curve",
  ].includes(factorName.toLowerCase())
}

function acceptablePrice(card: RecommendationCardType) {
  const gap = card.model_vs_market_gap
  if (!gap?.gap_direction) {
    return "Use fair market value unless the CTA or card action names a tighter price."
  }
  if (gap.gap_direction === "model_above") {
    return "You can pay near market; avoid adding a premium unless the manager fit is strong."
  }
  if (gap.gap_direction === "model_below") {
    return "Only proceed at a discount; do not pay the public-market sticker."
  }
  return "Fair market is acceptable; the edge comes from roster fit or timing."
}

function trendCopy(card: RecommendationCardType) {
  const trend = card.trend_result
  if (!trend) return null
  if (trend.trend_label === "will_rise") {
    return "Value trend: expected to gain market value."
  }
  if (trend.trend_label === "will_fall") {
    return "Value trend: downside risk is building."
  }
  return "Value trend: market value looks stable."
}

export function RecommendationCard({
  card,
  onCta,
}: {
  card: RecommendationCardType
  onCta?: (card: RecommendationCardType) => void
}) {
  const confidenceNote =
    card.confidence_label === "LOW"
      ? "Lower-confidence signal: treat this as a watchlist recommendation, not an automatic move."
      : null

  return (
    <Card className="border-border/60 bg-card/75">
      <CardContent className="space-y-4 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1">
            <p className="terminal-label text-muted-foreground">
              {card.recommendation_type}
            </p>
            <p className="text-base font-semibold">{card.headline}</p>
            <p className="text-sm leading-relaxed text-muted-foreground">
              <span className="font-medium text-foreground">One-sentence action:</span>{" "}
              {card.action}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <PriorityRankPill rank={card.priority_rank} />
            <ConfidenceBadge label={card.confidence_label} />
          </div>
        </div>

        <div className="space-y-1">
          <p className="terminal-label text-muted-foreground">What I Would Do</p>
          <p className="text-sm leading-relaxed text-muted-foreground">
            {card.why_summary}
          </p>
          <p className="text-sm leading-relaxed text-muted-foreground">
            <span className="font-medium text-foreground">Acceptable price:</span>{" "}
            {acceptablePrice(card)}
          </p>
        </div>

        {confidenceNote ? (
          <div className="rounded-lg border border-border/40 bg-card/45 px-3 py-2 text-xs text-muted-foreground">
            {confidenceNote}
          </div>
        ) : null}

        {card.supporting_factors.length > 0 ? (
          <div className="space-y-2">
            <p className="terminal-label text-muted-foreground">
              Supporting Factors
            </p>
            {card.supporting_factors.map((factor, index) =>
              isLikelyContextFlag(factor.factor_name) ? (
                <PlayerContextFlagRow
                  key={`${factor.factor_name}-${index}`}
                  flag={factor.factor_name}
                />
              ) : (
                <SupportingFactorRow
                  key={`${factor.factor_name}-${index}`}
                  factor={factor}
                />
              ),
            )}
          </div>
        ) : null}

        {card.model_vs_market_gap ? (
          <MarketGapPanel gap={card.model_vs_market_gap} />
        ) : null}

        {card.trend_result ? (
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <TrendBadge label={card.trend_result.trend_label} />
            <span>{card.trend_result.confidence} confidence</span>
            <span>{trendCopy(card)}</span>
          </div>
        ) : null}

        <Separator />

        <div className="space-y-2 text-sm text-muted-foreground">
          <p>
            <span className="font-medium text-foreground">Why now:</span>{" "}
            {card.why_summary}
          </p>
          <p>
            <span className="font-medium text-foreground">What would make this wrong:</span>{" "}
            {card.downside_of_inaction}
          </p>
          <p>
            <span className="font-medium text-foreground">Re-check if:</span>{" "}
            {card.what_would_change_this_call}
          </p>
          {card.league_specificity_notes ? (
            <p>
              <span className="font-medium text-foreground">
                League context:
              </span>{" "}
              {card.league_specificity_notes}
            </p>
          ) : null}
          {card.manager_specificity_notes ? (
            <p>
              <span className="font-medium text-foreground">
                Specific note:
              </span>{" "}
              {card.manager_specificity_notes}
            </p>
          ) : null}
        </div>

        {onCta ? (
          <Button variant="outline" size="sm" onClick={() => onCta(card)}>
            {card.cta_label}
          </Button>
        ) : (
          <a
            href={card.cta_destination}
            className={buttonClasses({ variant: "outline", size: "sm" })}
          >
            {card.cta_label}
          </a>
        )}
      </CardContent>
    </Card>
  )
}
