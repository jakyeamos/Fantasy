import { Link } from "@tanstack/react-router"

import type { HygieneSuggestion } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { buttonClasses } from "@/components/ui/button"

type HygieneSuggestionRowProps = {
  suggestion: HygieneSuggestion
  leagueId: string
}

const actionBadgeCopy: Record<HygieneSuggestion["action_type"], string> = {
  consolidate: "CONSOLIDATE",
  cut: "CUT",
  stash: "STASH",
  taxi: "TAXI",
  hold: "HOLD",
  shop: "SHOP",
  package: "PACKAGE",
  handcuff_speculative: "HANDCUFF",
  reroll_into_pick: "REROLL",
  throw_in_now: "THROW-IN",
}

const actionBadgeClass: Record<HygieneSuggestion["action_type"], string> = {
  consolidate: "border-sky-500/25 bg-sky-500/10 text-sky-700",
  cut: "border-destructive/25 bg-destructive/10 text-destructive",
  stash: "",
  taxi: "",
  hold: "border-emerald-500/25 bg-emerald-500/10 text-emerald-700",
  shop: "border-amber-500/25 bg-amber-500/10 text-amber-700",
  package: "border-sky-500/25 bg-sky-500/10 text-sky-700",
  handcuff_speculative: "border-violet-500/25 bg-violet-500/10 text-violet-700",
  reroll_into_pick: "border-orange-500/25 bg-orange-500/10 text-orange-700",
  throw_in_now: "border-orange-500/25 bg-orange-500/10 text-orange-700",
}

export function HygieneSuggestionRow({ suggestion, leagueId }: HygieneSuggestionRowProps) {
  const names = suggestion.primary_player_names.join(" + ")
  const target = suggestion.target_player_name != null ? ` -> ${suggestion.target_player_name}` : ""
  const badgeLabel = actionBadgeCopy[suggestion.action_type]
  const badgeClass = actionBadgeClass[suggestion.action_type]

  return (
    <div className="flex flex-col gap-1 py-3">
      <div className="flex flex-wrap items-center gap-2">
        <Badge
          variant={suggestion.action_type === "stash" ? "secondary" : "outline"}
          className={badgeClass}
        >
          {badgeLabel}
        </Badge>
        {/* TODO Phase 17: MarketGapBadge here once model_vs_market_gap is added to HygieneSuggestion. */}
        <span className="text-sm font-medium">
          {names}
          {target}
        </span>
      </div>
      <p className="text-sm text-muted-foreground leading-relaxed">{suggestion.reasoning}</p>
      <p className="text-xs text-muted-foreground">
        Timing: {suggestion.timing_rationale}
      </p>
      {suggestion.packaging_rationale ? (
        <p className="text-xs text-muted-foreground">
          Packaging: {suggestion.packaging_rationale}
        </p>
      ) : null}
      {suggestion.player_context_flags.length > 0 ? (
        <div className="flex flex-wrap gap-2 pt-1">
          {suggestion.player_context_flags.map((flag) => (
            <Badge key={flag} variant="outline" className="text-[11px]">
              {flag.replaceAll("_", " ")}
            </Badge>
          ))}
        </div>
      ) : null}
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
