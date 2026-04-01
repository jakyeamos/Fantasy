import type { ConfidenceLabel } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

const CONFIDENCE_CLASS: Record<ConfidenceLabel, string> = {
  HIGH: "border-emerald-500/25 bg-emerald-500/10 text-emerald-700",
  MEDIUM: "border-amber-400/25 bg-amber-400/10 text-amber-700",
  LOW: "border-border/50 bg-card/50 text-muted-foreground",
}

export function ConfidenceBadge({ label }: { label: ConfidenceLabel }) {
  return (
    <Badge variant="outline" className={cn("font-mono text-[11px]", CONFIDENCE_CLASS[label])}>
      {label}
    </Badge>
  )
}
