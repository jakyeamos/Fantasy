import type { RecommendationCard as RecommendationCardType } from "@/api/types"
import { ConfidenceBadge } from "@/components/recommendations/ConfidenceBadge"
import { MarketGapPanel } from "@/components/recommendations/MarketGapPanel"
import { PlayerContextFlagRow } from "@/components/recommendations/PlayerContextFlagRow"
import { PriorityRankPill } from "@/components/recommendations/PriorityRankPill"
import { SupportingFactorRow } from "@/components/recommendations/SupportingFactorRow"
import { Button, buttonClasses } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"

function isLikelyContextFlag(factorName: string) {
  return ["availability", "depth chart pressure", "role expansion", "role compression", "team context", "age curve"].includes(
    factorName.toLowerCase(),
  )
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
            <p className="terminal-label text-muted-foreground">{card.recommendation_type}</p>
            <p className="text-base font-semibold">{card.headline}</p>
            <p className="text-sm leading-relaxed text-muted-foreground">{card.action}</p>
          </div>
          <div className="flex items-center gap-2">
            <PriorityRankPill rank={card.priority_rank} />
            <ConfidenceBadge label={card.confidence_label} />
          </div>
        </div>

        <div className="space-y-1">
          <p className="terminal-label text-muted-foreground">Why This Call</p>
          <p className="text-sm leading-relaxed text-muted-foreground">{card.why_summary}</p>
        </div>

        {confidenceNote ? (
          <div className="rounded-lg border border-border/40 bg-card/45 px-3 py-2 text-xs text-muted-foreground">
            {confidenceNote}
          </div>
        ) : null}

        {card.supporting_factors.length > 0 ? (
          <div className="space-y-2">
            <p className="terminal-label text-muted-foreground">Supporting Factors</p>
            {card.supporting_factors.map((factor, index) =>
              isLikelyContextFlag(factor.factor_name) ? (
                <PlayerContextFlagRow key={`${factor.factor_name}-${index}`} flag={factor.factor_name} />
              ) : (
                <SupportingFactorRow key={`${factor.factor_name}-${index}`} factor={factor} />
              ),
            )}
          </div>
        ) : null}

        {card.model_vs_market_gap ? <MarketGapPanel gap={card.model_vs_market_gap} /> : null}

        <Separator />

        <div className="space-y-2 text-sm text-muted-foreground">
          <p>
            <span className="font-medium text-foreground">Downside:</span> {card.downside_of_inaction}
          </p>
          <p>
            <span className="font-medium text-foreground">What changes it:</span>{" "}
            {card.what_would_change_this_call}
          </p>
          {card.league_specificity_notes ? (
            <p>
              <span className="font-medium text-foreground">League context:</span>{" "}
              {card.league_specificity_notes}
            </p>
          ) : null}
          {card.manager_specificity_notes ? (
            <p>
              <span className="font-medium text-foreground">Specific note:</span>{" "}
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
