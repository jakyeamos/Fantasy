export function TierDivider({ label, playerCount }: { label: string; playerCount: number }) {
  return (
    <div className="mb-4 flex min-h-10 items-center justify-between rounded-xl border border-border/40 bg-card/45 px-4 py-3">
      <div>
        <p className="terminal-label text-muted-foreground">Tier</p>
        <p className="mt-2 font-headline text-2xl font-bold">{label}</p>
      </div>
      <p className="font-mono text-xs text-muted-foreground">{playerCount} players</p>
    </div>
  )
}
