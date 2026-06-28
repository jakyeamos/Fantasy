import { Badge } from "@/components/ui/badge"
import { badgeToneClasses } from "@/lib/ui-tokens"
import { cn } from "@/lib/utils"

export function HitRateBadge({
  bucket,
  lowConfidence,
}: {
  bucket: string
  lowConfidence: boolean
}) {
  if (lowConfidence) {
    return (
      <Badge variant="outline" className="text-muted-foreground">
        Low confidence
      </Badge>
    )
  }

  return (
    <Badge
      className={cn(
        "rounded px-2 py-0.5 text-xs font-medium",
        bucket === "High hit rate" && badgeToneClasses.success,
        bucket === "Moderate hit rate" && badgeToneClasses.warning,
        bucket === "Low hit rate" && badgeToneClasses.destructive,
      )}
    >
      {bucket}
    </Badge>
  )
}
