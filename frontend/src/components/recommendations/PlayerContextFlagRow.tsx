export function PlayerContextFlagRow({ flag }: { flag: string }) {
  return (
    <div className="rounded-md border border-border/40 bg-card/45 px-2 py-1 text-xs text-muted-foreground">
      {flag.replaceAll("_", " ")}
    </div>
  )
}
