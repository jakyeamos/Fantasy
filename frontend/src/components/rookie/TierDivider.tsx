export function TierDivider({
  label,
  playerCount,
}: {
  label: string
  playerCount: number
}) {
  return (
    <div className="mb-4 flex min-h-8 items-center justify-between rounded-sm bg-muted px-4 py-2">
      <p className="text-xl font-semibold">{label}</p>
      <p className="text-xs text-muted-foreground">{playerCount} players</p>
    </div>
  )
}
