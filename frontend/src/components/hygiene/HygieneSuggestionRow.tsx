import { Link } from "@tanstack/react-router"

import type { HygieneSuggestion } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { buttonClasses } from "@/components/ui/button"

type HygieneSuggestionRowProps = {
  suggestion: HygieneSuggestion
  leagueId: string
}

export function HygieneSuggestionRow({ suggestion, leagueId }: HygieneSuggestionRowProps) {
  const names = suggestion.primary_player_names.join(" + ")
  const target =
    suggestion.target_player_name != null
      ? ` → ${suggestion.target_player_name}`
      : ""

  return (
    <div className="flex flex-col gap-1 py-3">
      <div className="flex flex-wrap items-center gap-2">
        {suggestion.action_type === "consolidate" ? (
          <Badge variant="default">CONSOLIDATE</Badge>
        ) : null}
        {suggestion.action_type === "cut" ? (
          <Badge className="border-destructive/25 bg-destructive/10 text-destructive">CUT</Badge>
        ) : null}
        {suggestion.action_type === "stash" ? (
          <Badge variant="secondary">STASH</Badge>
        ) : null}
        {suggestion.action_type === "taxi" ? (
          <Badge variant="outline">TAXI</Badge>
        ) : null}
        <span className="text-sm font-medium">
          {names}
          {target}
        </span>
      </div>
      <p className="text-sm text-muted-foreground leading-relaxed">{suggestion.reasoning}</p>
      {suggestion.action_type === "consolidate" && suggestion.counterparty_name ? (
        <div className="flex flex-col items-start gap-1">
          <p className="text-xs text-muted-foreground">
            Target manager:{" "}
            <span className="font-medium text-foreground">{suggestion.counterparty_name}</span>
          </p>
          <Link
            to="/trades"
            search={{ leagueId }}
            className={buttonClasses({ variant: "ghost", size: "sm" })}
          >
            Evaluate This Package
          </Link>
        </div>
      ) : null}
    </div>
  )
}
