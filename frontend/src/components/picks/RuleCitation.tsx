import { Link } from "@tanstack/react-router"

export function RuleCitation({
  citation,
  leagueId,
}: {
  citation: string | null
  leagueId: string
}) {
  if (citation) {
    return (
      <Link
        to="/league/$leagueId"
        params={{ leagueId }}
        hash="draft-order-rule"
        className="mt-1 block text-xs text-muted-foreground"
      >
        {citation}
      </Link>
    )
  }

  return (
    <Link
      to="/league/$leagueId"
      params={{ leagueId }}
      hash="draft-order-rule"
      className="mt-1 block text-xs text-primary underline"
    >
      Rule not configured - set it up
    </Link>
  )
}
