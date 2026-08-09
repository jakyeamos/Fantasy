import type { HygieneSuggestion } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

type DeadRosterPanelProps = {
  suggestions: HygieneSuggestion[]
}

export function DeadRosterPanel({ suggestions }: DeadRosterPanelProps) {
  const cutSuggestions = suggestions.filter((suggestion) => suggestion.action_type === "cut")

  return (
    <Card>
      <CardHeader>
        <p className="terminal-label text-muted-foreground">Dead Roster Spots</p>
        <CardTitle>Bench Cleanup</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {cutSuggestions.length ? (
          cutSuggestions.map((suggestion, index) => (
            <div
              key={`${suggestion.primary_player_ids.join("-")}-${index}`}
              className="rounded-lg border border-border/50 bg-card/35 px-4 py-3"
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-semibold">
                  {suggestion.primary_player_names.join(", ")}
                </span>
                <Badge className="border-destructive/25 bg-destructive/10 text-destructive">
                  DEAD
                </Badge>
              </div>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">{suggestion.reasoning}</p>
            </div>
          ))
        ) : (
          <p className="text-sm leading-6 text-muted-foreground">No dead roster spots detected.</p>
        )}
      </CardContent>
    </Card>
  )
}
