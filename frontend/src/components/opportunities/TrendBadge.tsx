import type { TrendLabel } from "@/api/types"
import { cn } from "@/lib/utils"

const trendClasses: Record<TrendLabel, string> = {
  will_rise: "border-primary/25 bg-primary/10 text-primary",
  will_maintain: "border-accent/20 bg-accent/10 text-accent-foreground",
  will_fall: "border-destructive/25 bg-destructive/10 text-destructive",
}

const trendCopy: Record<TrendLabel, string> = {
  will_rise: "WILL RISE",
  will_maintain: "WILL MAINTAIN",
  will_fall: "WILL FALL",
}

export function TrendBadge({ label }: { label: TrendLabel }) {
  return (
    <span
      className={cn(
        "terminal-label inline-flex items-center rounded-md border px-2.5 py-1",
        trendClasses[label],
      )}
    >
      {trendCopy[label]}
    </span>
  )
}
