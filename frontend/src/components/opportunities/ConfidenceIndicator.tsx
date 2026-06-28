import type { TrendConfidence } from "@/api/types"
import { Badge } from "@/components/ui/badge"

const confidenceCopy: Record<TrendConfidence, string> = {
  HIGH: "HIGH CONF",
  MEDIUM: "MED CONF",
  LOW: "LOW CONF",
}

export function ConfidenceIndicator({
  confidence,
}: {
  confidence: TrendConfidence
}) {
  return (
    <Badge variant="outline" className="text-label-xs text-muted-foreground">
      {confidenceCopy[confidence]}
    </Badge>
  )
}
