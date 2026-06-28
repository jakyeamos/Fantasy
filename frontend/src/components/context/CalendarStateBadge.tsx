import type { CalendarState } from "@/api/types"
import { seasonBadgeClasses } from "@/lib/ui-tokens"
import { cn } from "@/lib/utils"

const LABELS: Record<CalendarState, string> = {
  startup: "Startup Draft",
  preseason: "Preseason",
  early_season: "Early Season",
  trade_deadline: "Trade Deadline",
  playoffs: "Playoffs",
  rookie_fever: "Rookie Fever",
  post_combine: "Post-Combine",
  post_nfl_draft: "Post-NFL Draft",
}

export function CalendarStateBadge({
  state,
  className,
}: {
  state: CalendarState
  className?: string
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium",
        seasonBadgeClasses[state],
        className,
      )}
    >
      {LABELS[state]}
    </span>
  )
}
