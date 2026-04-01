import type { SuggestedAction } from "@/api/types"
import { cn } from "@/lib/utils"

const actionClasses: Record<SuggestedAction, string> = {
  buy: "border-primary/25 bg-primary/10 text-primary",
  hold: "border-accent/20 bg-accent/10 text-accent-foreground",
  sell: "border-destructive/25 bg-destructive/10 text-destructive",
}

const actionCopy: Record<SuggestedAction, string> = {
  buy: "BUY",
  hold: "HOLD",
  sell: "SELL",
}

export function SuggestedActionBadge({ action }: { action: SuggestedAction }) {
  return (
    <span
      className={cn(
        "terminal-label inline-flex items-center rounded-md border px-2.5 py-1",
        actionClasses[action],
      )}
    >
      {actionCopy[action]}
    </span>
  )
}
