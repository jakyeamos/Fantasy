import type { DimensionScore } from "@/api/types"

export function DimensionScoreRow({
  label,
  score,
}: {
  label: string
  score: DimensionScore
}) {
  const scoreColor =
    score.score >= 80
      ? "text-green-600"
      : score.score >= 50
        ? "text-foreground"
        : "text-red-600"

  return (
    <div className="space-y-2 border-t border-border/60 py-3 first:border-t-0">
      <div className="flex items-center gap-3">
        <div className="w-40 shrink-0 text-xs text-foreground">
          {label}
          {score.confidence === "LOW" ? (
            <span className="ml-2 italic text-muted-foreground">(low confidence)</span>
          ) : null}
        </div>
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full bg-primary transition-all"
            style={{ width: `${score.score}%` }}
          />
        </div>
        <div className={`w-10 text-right text-xs ${scoreColor}`}>
          {score.score.toFixed(0)}
        </div>
      </div>
      <p className="text-sm text-muted-foreground">{score.reasoning}</p>
    </div>
  )
}
