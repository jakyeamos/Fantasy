import { Badge } from "@/components/ui/badge"
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
        bucket === "High hit rate" && "bg-green-50 text-green-700 dark:bg-green-950/20 dark:text-green-300",
        bucket === "Moderate hit rate" &&
          "bg-amber-50 text-amber-700 dark:bg-amber-950/20 dark:text-amber-300",
        bucket === "Low hit rate" && "bg-red-50 text-red-600 dark:bg-red-950/20 dark:text-red-400",
      )}
    >
      {bucket}
    </Badge>
  )
}
