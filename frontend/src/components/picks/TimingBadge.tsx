import type { TimingLabel } from "@/api/types"
import { badgeToneClasses } from "@/lib/ui-tokens"
import { cn } from "@/lib/utils"

const LABELS: Record<TimingLabel, string> = {
  sell_now: "Sell now",
  hold_until_rookie_fever: "Hold",
  use_on_the_clock: "On the clock",
}

const CLASSES: Record<TimingLabel, string> = {
  sell_now: badgeToneClasses.warning,
  hold_until_rookie_fever: badgeToneClasses.info,
  use_on_the_clock: badgeToneClasses.success,
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
