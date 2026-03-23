import type { TradeVerdict } from "@/api/types"
import { cn } from "@/lib/utils"

export function VerdictBanner({ verdict }: { verdict: TradeVerdict }) {
  const classes =
    verdict.verdict === "trade"
      ? "bg-amber-100 text-amber-800 dark:bg-amber-950/30 dark:text-amber-200"
      : "bg-green-50 text-green-700 dark:bg-green-950/20 dark:text-green-300"

  return (
    <div className={cn("rounded-xl p-4", classes)}>
      <p className="text-xl font-semibold">{verdict.label}</p>
      <p className="mt-1 text-sm text-current/90">{verdict.reasoning}</p>
    </div>
  )
}
