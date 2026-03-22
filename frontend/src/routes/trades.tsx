import { createFileRoute } from "@tanstack/react-router"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export const Route = createFileRoute("/trades")({
  validateSearch: (search: Record<string, unknown>) => ({
    leagueId: typeof search.leagueId === "string" ? search.leagueId : undefined,
  }),
  component: TradesPlaceholderPage,
})

function TradesPlaceholderPage() {
  const search = Route.useSearch()

  return (
    <Card>
      <CardHeader>
        <CardTitle>Evaluate Trade</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <p className="text-sm text-muted-foreground">
          Trade evaluator shell is ready.
        </p>
        {search.leagueId ? (
          <p className="text-sm text-muted-foreground">
            Selected league: <span className="font-medium text-foreground">{search.leagueId}</span>
          </p>
        ) : null}
      </CardContent>
    </Card>
  )
}
