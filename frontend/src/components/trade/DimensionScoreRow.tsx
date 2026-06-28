import type { DimensionScore } from "@/api/types"
import { textToneClasses } from "@/lib/ui-tokens"

export function DimensionScoreRow({
  label,
  score,
}: {
  label: string
  score: DimensionScore
}) {
  const scoreColor =
    score.score >= 80
      ? textToneClasses.success
      : score.score >= 50
        ? "text-foreground"
        : textToneClasses.destructive

  return (
    <div className="space-y-2 border-t border-border/45 py-4 first:border-t-0">
      <div className="flex items-center gap-3">
        <div className="w-40 shrink-0 text-xs text-foreground">
          {label}
          {score.confidence === "LOW" ? (
            <span className="ml-2 italic text-muted-foreground">(low confidence)</span>
          ) : null}
        </div>
        <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full bg-gradient-to-r from-primary/60 to-primary transition-all"
            style={{ width: `${score.score}%` }}
          />
        </div>
        <div className={`w-12 text-right font-mono text-xs ${scoreColor}`}>
          {score.score.toFixed(0)}
        </div>
      </div>
      <p className="text-sm text-muted-foreground">{score.reasoning}</p>
    </div>
  )
}
