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
        <p className="mt-3 text-sm leading-6 text-muted-foreground">{recommendation.rationale}</p>
      ) : null}
    </div>
  )
}
