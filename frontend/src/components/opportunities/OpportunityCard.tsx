import type { OpportunityFeedItem } from "@/api/types"
import { Link } from "@tanstack/react-router"
import { AlertTriangle, ArrowRightLeft, ExternalLink, Gauge, Target, UserRound } from "lucide-react"

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

function availabilityLabel(availability: OpportunityFeedItem["availability"]) {
  if (availability === "my_roster") return "My roster"
  if (availability === "opponent_roster") return "Opponent-owned"
  return "Available"
}

export function OpportunityCard({
  item,
  rank,
}: {
  item: OpportunityFeedItem
  rank: number
}) {
  const ctaTarget = buildOpportunityCtaTarget(item)
  const similarPlayerEvidenceIsStale =
    item.similar_players.length > 0 && item.evidence_freshness.is_stale

  return (
    <Card className="group overflow-hidden border-border/55 bg-card/70">
      <CardContent className="grid gap-4 p-0 sm:grid-cols-[72px_minmax(0,1fr)]">
        <div className="flex items-center justify-between border-b border-border/45 bg-secondary/25 px-5 py-4 sm:block sm:border-b-0 sm:border-r sm:px-4">
          <p className="terminal-label text-muted-foreground">Rank</p>
          <p className="font-headline text-3xl font-extrabold text-primary">
            {String(rank).padStart(2, "0")}
          </p>
        </div>

        <div className="space-y-4 px-5 pb-5 sm:px-5 sm:py-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="min-w-0 flex-1 space-y-2">
              <CalendarEscalationLabel label={item.calendar_escalation_label} />

              <div className="flex flex-wrap items-center gap-2">
                <p className="text-base font-bold text-foreground">
                  {item.player_name}
                </p>
                <Badge variant="outline">{item.position}</Badge>
                <Badge variant={item.availability === "available" ? "secondary" : "outline"}>
                  {availabilityLabel(item.availability)}
                </Badge>
                <OwnershipSymbol leagueIds={item.owned_in_leagues} />
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2 lg:justify-end">
              <SuggestedActionBadge action={item.suggested_action} />
              <div className="inline-flex items-center gap-2 rounded-lg border border-border/55 bg-background/35 px-3 py-2">
                <Gauge className="size-4 text-primary" />
                <div>
                  <p className="terminal-label text-muted-foreground">Impact</p>
                  <p className="font-mono text-sm font-bold text-foreground">
                    {Math.round(item.impact_score)}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2.5 rounded-lg border border-border/40 bg-background/25 px-3 py-2">
            <TrendBadge label={item.trend_label} />
            <span className="font-mono text-xs text-muted-foreground">
              ADP Gap: {formatGap(item.adp_gap)}
            </span>
            <ConfidenceIndicator confidence={item.trend_confidence} />
            {item.weekly_fit ? (
              <Badge
                variant="outline"
                className="gap-1.5 border-primary/25 bg-primary/10 text-primary"
              >
                <Target className="size-3" />
                Solves {item.weekly_fit.position} gap
              </Badge>
            ) : null}
            {item.weekly_fit?.is_stale ? (
              <Badge
                variant="outline"
                className="gap-1.5 border-warning/25 bg-warning-surface text-warning"
              >
                <AlertTriangle className="size-3" />
                Stale weekly data
              </Badge>
            ) : null}
            {similarPlayerEvidenceIsStale ? (
              <Badge
                variant="outline"
                className="gap-1.5 border-warning/25 bg-warning-surface text-warning"
              >
                <AlertTriangle className="size-3" />
                Stale comp evidence
              </Badge>
            ) : null}
          </div>

          {item.weekly_fit ? (
            <div className="rounded-lg border border-primary/20 bg-primary/10 px-3 py-2 text-xs leading-5 text-primary">
              What I would check: {item.weekly_fit.player_name} is{" "}
              {item.weekly_fit.gap_to_title_target.toFixed(1)} below the title target at{" "}
              {item.weekly_fit.position}.{" "}
              {item.weekly_fit.is_stale
                ? `Refresh ${item.weekly_fit.stale_domains.join(", ")} before acting.`
                : "Weekly data is fresh enough to use this as a lineup-fit tiebreaker."}
            </div>
          ) : null}

          <p className="text-sm leading-relaxed text-muted-foreground">
            {item.why_summary}
          </p>

          {item.trend_confidence === "LOW" ? (
            <p className="text-xs italic text-muted-foreground">
              Limited projection confidence. Treat as directional.
            </p>
          ) : null}

          <ConflictExplanationPanel explanation={item.conflict_explanation} />
          {similarPlayerEvidenceIsStale ? (
            <div className="flex items-center gap-2 rounded-lg border border-warning/25 bg-warning-surface px-3 py-2 text-xs leading-5 text-warning">
              <AlertTriangle className="size-3.5 shrink-0" />
              Refresh {item.evidence_freshness.stale_domains.join(", ")} before
              relying on similar-player comps.
            </div>
          ) : null}
          <SimilarPlayersSection players={item.similar_players} />

          {ctaTarget ? (
            <div className="flex flex-wrap items-center gap-2 border-t border-border/45 pt-4">
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
        </div>
      </CardContent>
    </Card>
  )
}
