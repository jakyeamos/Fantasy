import { TrendingDown, TrendingUp, Minus } from "lucide-react"

import type { StrategicDistinction } from "@/api/types"

export function StrategicDistinctionBanner({
  distinction,
}: {
  distinction: StrategicDistinction
}) {
  const isNeutral = distinction.verdict === "neutral"
  const Icon =
    distinction.verdict === "advancing"
      ? TrendingUp
      : distinction.verdict === "negative"
        ? TrendingDown
        : Minus

  return (
    <div
      className={`glass-panel flex items-start gap-3 rounded-xl border p-5 ${
        isNeutral
          ? "border-border/45 bg-card/50"
          : "border-primary/25 bg-primary/10"
      }`}
    >
      <Icon className={isNeutral ? "text-muted-foreground" : "text-primary"} />
      <div className="space-y-1">
        <p className="terminal-label text-muted-foreground">
          Strategic distinction
        </p>
        <p className="font-headline text-2xl font-bold">
          {distinction.headline}
        </p>
        <p
          className={`text-sm ${isNeutral ? "text-muted-foreground" : "text-foreground"}`}
        >
          {distinction.explanation}
        </p>
      </div>
    </div>
  )
}
