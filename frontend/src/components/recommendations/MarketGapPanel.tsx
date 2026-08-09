import type { ModelVsMarketGap } from "@/api/types"

import { MarketGapBadge } from "@/components/recommendations/MarketGapBadge"

function formatMaybeNumber(value: number | null) {
  if (value == null) return "—"
  return Number.isInteger(value) ? String(value) : value.toFixed(2)
}

export function MarketGapPanel({ gap }: { gap: ModelVsMarketGap }) {
  return (
    <div className="rounded-lg border border-border/40 bg-card/45 p-3">
      <div className="flex flex-wrap items-center gap-2">
        <p className="terminal-label text-muted-foreground">Market Gap</p>
        {gap.gap_classification ? (
          <MarketGapBadge classification={gap.gap_classification} />
        ) : null}
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
        <div>
          <p className="terminal-label text-muted-foreground">Model</p>
          <p>{formatMaybeNumber(gap.model_value)}</p>
          <p className="text-xs text-muted-foreground">
            Rank {formatMaybeNumber(gap.model_rank)}
          </p>
        </div>
        <div>
          <p className="terminal-label text-muted-foreground">Market</p>
          <p>{formatMaybeNumber(gap.market_value)}</p>
          <p className="text-xs text-muted-foreground">
            Rank {formatMaybeNumber(gap.market_rank)}
          </p>
        </div>
      </div>
      {gap.explanation ? (
        <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
          {gap.explanation}
        </p>
      ) : null}
    </div>
  )
}
