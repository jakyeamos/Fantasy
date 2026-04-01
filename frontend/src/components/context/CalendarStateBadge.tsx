import type { CalendarState } from "@/api/types"
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

const CLASSES: Record<CalendarState, string> = {
  startup: "bg-rose-100 text-rose-900 dark:bg-rose-950/30 dark:text-rose-200",
  preseason: "bg-amber-100 text-amber-900 dark:bg-amber-950/30 dark:text-amber-200",
  early_season: "bg-emerald-100 text-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-200",
  trade_deadline: "bg-orange-100 text-orange-900 dark:bg-orange-950/30 dark:text-orange-200",
  playoffs: "bg-sky-100 text-sky-900 dark:bg-sky-950/30 dark:text-sky-200",
  rookie_fever: "bg-red-100 text-red-900 dark:bg-red-950/30 dark:text-red-200",
  post_combine: "bg-indigo-100 text-indigo-900 dark:bg-indigo-950/30 dark:text-indigo-200",
  post_nfl_draft: "bg-teal-100 text-teal-900 dark:bg-teal-950/30 dark:text-teal-200",
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
        CLASSES[state],
        className,
      )}
    >
      {LABELS[state]}
    </span>
  )
}
