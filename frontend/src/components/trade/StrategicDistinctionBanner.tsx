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
      className={`flex items-start gap-3 rounded-xl border-l-4 p-4 ${
        isNeutral
          ? "border-muted-foreground/30 bg-muted"
          : "border-amber-500 bg-amber-50 text-amber-900"
      }`}
    >
      <Icon className={isNeutral ? "text-muted-foreground" : "text-amber-600"} />
      <div className="space-y-1">
        <p className="text-xl font-semibold">{distinction.headline}</p>
        <p className={`text-sm ${isNeutral ? "text-muted-foreground" : "text-amber-800"}`}>
          {distinction.explanation}
        </p>
      </div>
    </div>
  )
}
