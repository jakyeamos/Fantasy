import { useState } from "react"

import { ChevronDown } from "lucide-react"

import type { WaiverRecommendation } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

type WaiverPlayerRowProps = {
  recommendation: WaiverRecommendation
}

function urgencyVariant(urgency: WaiverRecommendation["urgency"]) {
  if (urgency === "High") return "default"
  if (urgency === "Medium") return "secondary"
  return "outline"
}

function confidenceVariant(confidence: WaiverRecommendation["confidence"]) {
  if (confidence === "HIGH") return "default"
  if (confidence === "MEDIUM") return "secondary"
  return "outline"
}

export function WaiverPlayerRow({ recommendation }: WaiverPlayerRowProps) {
  const [showRationale, setShowRationale] = useState(false)

  return (
    <div className="py-4">
      <button
        type="button"
        onClick={() => setShowRationale((value) => !value)}
        className="flex w-full items-start justify-between gap-4 text-left"
      >
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold">{recommendation.player_name}</span>
            <Badge variant="outline">{recommendation.position}</Badge>
            {recommendation.team ? (
              <span className="text-xs text-muted-foreground">{recommendation.team}</span>
            ) : null}
            {recommendation.is_immediate_start ? <Badge variant="secondary">Startable</Badge> : null}
            {recommendation.dynasty_stash ? <Badge variant="outline">Stash</Badge> : null}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {recommendation.recommendation_label === "free_agent_only" ? (
              <Badge className="border-accent/30 bg-accent/20 text-accent">Free Claim</Badge>
            ) : (
              <span className="font-mono text-sm">
                {recommendation.bid_low === null
                  ? "Priority waiver"
                  : `$${recommendation.bid_low ?? 0} / $${recommendation.bid_mid ?? 0} / $${recommendation.bid_high ?? 0}`}
              </span>
            )}
            <Badge variant={urgencyVariant(recommendation.urgency)}>{recommendation.urgency}</Badge>
            <Badge variant={confidenceVariant(recommendation.confidence)}>
              {recommendation.confidence}
            </Badge>
          </div>
          <div className="grid gap-2 text-xs text-muted-foreground sm:grid-cols-2">
            <span>
              <span className="font-semibold text-foreground">Fit:</span>{" "}
              {recommendation.roster_fit}
            </span>
            <span>
              <span className="font-semibold text-foreground">Drop:</span>{" "}
              {recommendation.drop_candidate ?? "lowest bench churn asset"}
            </span>
          </div>
        </div>
        <ChevronDown
          className={cn(
            "mt-1 size-4 shrink-0 text-muted-foreground",
            showRationale ? "rotate-180" : "",
          )}
        />
      </button>
      {showRationale ? (
        <div className="mt-3 space-y-2 text-sm leading-6 text-muted-foreground">
          <p>{recommendation.rationale}</p>
          {recommendation.drop_reason ? <p>{recommendation.drop_reason}</p> : null}
          {recommendation.data_freshness_warning ? (
            <p className="text-orange-300">
              Waiver budgets or roster state may be stale; refresh before bidding.
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
