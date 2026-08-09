import type { TradeVerdict } from "@/api/types"
import { cn } from "@/lib/utils"

export function VerdictBanner({ verdict }: { verdict: TradeVerdict }) {
  const classes =
    verdict.verdict === "trade"
      ? "border-primary/25 bg-primary/10 text-foreground"
      : "border-accent/20 bg-accent/10 text-foreground"

  return (
    <div className={cn("glass-panel rounded-xl border p-5", classes)}>
      <p className="terminal-label text-muted-foreground">Draft verdict</p>
      <p className="mt-2 font-headline text-3xl font-extrabold">
        {verdict.label}
      </p>
      <p className="mt-2 text-sm text-current/90">{verdict.reasoning}</p>
    </div>
  )
}
