import type { OpportunityFeedItem } from "@/api/types"
import { Link } from "@tanstack/react-router"
import { ArrowRightLeft, ExternalLink, UserRound } from "lucide-react"

import { CalendarEscalationLabel } from "@/components/opportunities/CalendarEscalationLabel"
import { ConfidenceIndicator } from "@/components/opportunities/ConfidenceIndicator"
import { ConflictExplanationPanel } from "@/components/opportunities/ConflictExplanationPanel"
import { OwnershipSymbol } from "@/components/opportunities/OwnershipSymbol"
import { SimilarPlayersSection } from "@/components/opportunities/SimilarPlayersSection"
import { SuggestedActionBadge } from "@/components/opportunities/SuggestedActionBadge"
import { TrendBadge } from "@/components/opportunities/TrendBadge"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { buttonClasses } from "@/components/ui/button"
import { buildOpportunityCtaTarget } from "@/lib/opportunityCta"

function formatGap(adpGap: number) {
  const rounded = Math.round(adpGap)
  return rounded >= 0 ? `+${rounded}` : String(rounded)
}

export function OpportunityCard({
  item,
}: {
  item: OpportunityFeedItem
}) {
  const ctaTarget = buildOpportunityCtaTarget(item)

  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <CalendarEscalationLabel label={item.calendar_escalation_label} />

            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-bold text-foreground">{item.player_name}</p>
              <Badge variant="outline">{item.position}</Badge>
              <OwnershipSymbol leagueIds={item.owned_in_leagues} />
            </div>
          </div>

          <SuggestedActionBadge action={item.suggested_action} />
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2.5">
          <TrendBadge label={item.trend_label} />
          <span className="font-mono text-xs text-muted-foreground">
            ADP Gap: {formatGap(item.adp_gap)}
          </span>
          <span className="terminal-label text-muted-foreground">
            IMPACT {Math.round(item.impact_score)}
          </span>
          <ConfidenceIndicator confidence={item.trend_confidence} />
        </div>

        <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
          {item.why_summary}
        </p>

        {item.trend_confidence === "LOW" ? (
          <p className="mt-2 text-xs italic text-muted-foreground">
            Limited projection confidence. Treat as directional.
          </p>
        ) : null}

        <ConflictExplanationPanel explanation={item.conflict_explanation} />
        <SimilarPlayersSection players={item.similar_players} />

        {ctaTarget ? (
          <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-border/45 pt-4">
            {ctaTarget.kind === "trade_evaluator" ? (
              <Link
                to="/trades"
                search={ctaTarget.search}
                className={buttonClasses({ variant: "default", size: "sm" })}
              >
                <ArrowRightLeft className="size-3.5" />
                {ctaTarget.label}
              </Link>
            ) : null}
            {ctaTarget.kind === "manager_dossier" ? (
              <Link
                to="/league/$leagueId/managers/$managerId"
                params={ctaTarget.params}
                className={buttonClasses({ variant: "outline", size: "sm" })}
              >
                <UserRound className="size-3.5" />
                {ctaTarget.label}
              </Link>
            ) : null}
            {ctaTarget.kind === "player_rankings" ? (
              <Link
                to="/league/$leagueId/player-rankings"
                params={ctaTarget.params}
                className={buttonClasses({ variant: "outline", size: "sm" })}
              >
                <ExternalLink className="size-3.5" />
                {ctaTarget.label}
              </Link>
            ) : null}
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
