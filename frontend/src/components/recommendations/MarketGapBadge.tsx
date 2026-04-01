import type { GapClassification } from "@/api/types"
import { Badge } from "@/components/ui/badge"
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
  buy_low: "border-primary/25 bg-primary/10 text-primary",
  sell_high: "border-amber-400/25 bg-amber-400/10 text-amber-600 dark:text-amber-300",
  hold_despite_weak_market: "border-accent/20 bg-accent/10 text-accent-foreground",
  ignore_false_discount: "border-border/40 bg-card/45 text-muted-foreground",
  market_right_model_cautious: "border-border/40 bg-card/45 text-muted-foreground",
  league_specific_opportunity: "border-primary/25 bg-primary/10 text-primary",
}

export function MarketGapBadge({ classification }: { classification: GapClassification }) {
  return (
    <Badge variant="outline" className={cn("text-[11px]", GAP_CLASS[classification])}>
      {GAP_LABEL[classification]}
    </Badge>
  )
}
