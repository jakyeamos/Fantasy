import type { CalendarContext } from "@/api/types"
import { CalendarStateBadge } from "@/components/context/CalendarStateBadge"

export function CalendarContextPanel({
  context,
}: {
  context: CalendarContext
}) {
  return (
    <div className="rounded-xl border border-border/45 bg-card/45 p-4 text-sm">
      <div className="mb-2 flex items-center justify-between gap-3">
        <span className="terminal-label text-muted-foreground">Calendar state</span>
        <CalendarStateBadge state={context.active_state} />
      </div>
      <p className="text-xs leading-5 text-muted-foreground">
        Auto-detected from the current calendar and shared across the app as a
        single source of truth.
      </p>
    </div>
  )
}
