import { Link } from "@tanstack/react-router"

import type { HygieneSuggestion } from "@/api/types"
import { MarketGapBadge } from "@/components/recommendations/MarketGapBadge"
import { Badge } from "@/components/ui/badge"
import { buttonClasses } from "@/components/ui/button"
import { badgeToneClasses } from "@/lib/ui-tokens"

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
  consolidate: badgeToneClasses.info,
  cut: badgeToneClasses.destructive,
  stash: "",
  taxi: "",
  hold: badgeToneClasses.success,
  shop: badgeToneClasses.warning,
  package: badgeToneClasses.info,
  handcuff_speculative: badgeToneClasses.strategy,
  reroll_into_pick: badgeToneClasses.attention,
  throw_in_now: badgeToneClasses.attention,
}

export function HygieneSuggestionRow({
  suggestion,
  leagueId,
}: HygieneSuggestionRowProps) {
  const names = suggestion.primary_player_names.join(" + ")
  const target =
    suggestion.target_player_name != null
      ? ` -> ${suggestion.target_player_name}`
      : ""
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
        {suggestion.model_vs_market_gap?.gap_classification ? (
          <MarketGapBadge
            classification={suggestion.model_vs_market_gap.gap_classification}
          />
        ) : null}
        <span className="text-sm font-medium">
          {names}
          {target}
        </span>
      </div>
      <p className="text-sm text-muted-foreground leading-relaxed">
        {suggestion.reasoning}
      </p>
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
            <Badge key={flag} variant="outline" className="text-label-sm">
              {flag.replaceAll("_", " ")}
            </Badge>
          ))}
        </div>
      ) : null}
      {suggestion.action_type === "consolidate" &&
      suggestion.counterparty_name ? (
        <div className="flex flex-col items-start gap-1">
          <p className="text-xs text-muted-foreground">
            Target manager:{" "}
            <span className="font-medium text-foreground">
              {suggestion.counterparty_name}
            </span>
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
