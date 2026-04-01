export function PriorityRankPill({ rank }: { rank: number }) {
  return (
    <span className="rounded-md border border-border/60 bg-card/60 px-2 py-1 font-mono text-xs text-foreground">
      #{String(rank).padStart(2, "0")}
    </span>
  )
}
