import type { TimingLabel } from "@/api/types"
import { cn } from "@/lib/utils"

const LABELS: Record<TimingLabel, string> = {
  sell_now: "Sell now",
  hold_until_rookie_fever: "Hold",
  use_on_the_clock: "On the clock",
}

const CLASSES: Record<TimingLabel, string> = {
  sell_now: "bg-amber-100 text-amber-800 dark:bg-amber-950/30 dark:text-amber-200",
  hold_until_rookie_fever:
    "bg-blue-50 text-blue-700 dark:bg-blue-950/20 dark:text-blue-300",
  use_on_the_clock:
    "bg-green-50 text-green-700 dark:bg-green-950/20 dark:text-green-300",
}

export function TimingBadge({
  label,
  reasoning,
  showReasoning = true,
  className,
}: {
  label: TimingLabel
  reasoning: string
  showReasoning?: boolean
  className?: string
}) {
  return (
    <div className={cn("flex flex-col gap-1", className)}>
      <span className={cn("w-fit rounded px-2 py-1 text-xs font-medium", CLASSES[label])}>
        {LABELS[label]}
      </span>
      {showReasoning ? <span className="text-xs text-muted-foreground">{reasoning}</span> : null}
    </div>
  )
}
