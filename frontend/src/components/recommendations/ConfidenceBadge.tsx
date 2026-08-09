import type { ConfidenceLabel } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { badgeToneClasses } from "@/lib/ui-tokens"
import { cn } from "@/lib/utils"

const CONFIDENCE_CLASS: Record<ConfidenceLabel, string> = {
  HIGH: badgeToneClasses.success,
  MEDIUM: badgeToneClasses.warning,
  LOW: badgeToneClasses.neutral,
}

export function ConfidenceBadge({ label }: { label: ConfidenceLabel }) {
  return (
    <Badge
      variant="outline"
      className={cn("font-mono text-label-sm", CONFIDENCE_CLASS[label])}
    >
      {label}
    </Badge>
  )
}
