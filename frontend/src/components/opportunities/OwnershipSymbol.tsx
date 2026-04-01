import { CircleDot } from "lucide-react"

export function OwnershipSymbol({ leagueIds }: { leagueIds: string[] }) {
  if (leagueIds.length === 0) {
    return null
  }

  return (
    <span className="inline-flex items-center gap-1.5">
      <CircleDot className="size-3 text-primary" />
      <span className="terminal-label text-primary/85">
        {leagueIds.join(", ")}
      </span>
    </span>
  )
}
