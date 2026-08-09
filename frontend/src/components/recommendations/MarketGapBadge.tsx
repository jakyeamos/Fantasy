import type { GapClassification } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { badgeToneClasses } from "@/lib/ui-tokens"
import { cn } from "@/lib/utils"

const GAP_LABEL: Record<GapClassification, string> = {
  buy_low: "BUY LOW",
  sell_high: "SELL HIGH",
  hold_despite_weak_market: "HOLD DESPITE WEAK MARKET",
  ignore_false_discount: "IGNORE FALSE DISCOUNT",
  market_right_model_cautious: "MARKET RIGHT / MODEL CAUTIOUS",
  league_specific_opportunity: "LEAGUE-SPECIFIC OPPORTUNITY",
}

const GAP_CLASS: Record<GapClassification, string> = {
  buy_low: badgeToneClasses.primary,
  sell_high: badgeToneClasses.warning,
  hold_despite_weak_market: badgeToneClasses.accent,
  ignore_false_discount: badgeToneClasses.neutral,
  market_right_model_cautious: badgeToneClasses.neutral,
  league_specific_opportunity: badgeToneClasses.primary,
}

export function MarketGapBadge({
  classification,
}: {
  classification: GapClassification
}) {
  return (
    <Badge
      variant="outline"
      className={cn("text-label-sm", GAP_CLASS[classification])}
    >
      {GAP_LABEL[classification]}
    </Badge>
  )
}
