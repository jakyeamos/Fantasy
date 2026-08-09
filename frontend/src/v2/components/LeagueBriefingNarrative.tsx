import type { LeagueDetailResponse, LineupResult } from "@/api/types"
import type { DecisionCard as DecisionCardModel } from "@/v2/contracts/decision-card"
import { DecisionCard } from "@/v2/components/DecisionCard"
import { StatePanel } from "@/v2/components/StatePanel"

export function LeagueBriefingNarrative({
  league,
  leagueId,
  rosterId,
  lineup,
}: {
  league: LeagueDetailResponse
  leagueId: string
  rosterId: number | null
  lineup: LineupResult | null
}) {
  if (!rosterId) {
    return (
      <StatePanel
        state="blocked"
        title="Roster context is required"
        body="This league can be inspected, but a linked roster is required before the briefing can recommend a move."
      />
    )
  }

  const confidence = league.confidence_band.toLowerCase()
  const band =
    confidence === "high" || confidence === "medium" ? confidence : "low"
  const action = lineup?.upgrade_leverage_point
    ? `Start with ${lineup.upgrade_leverage_point}. ${league.primary_weakness}`
    : league.primary_weakness
  const card: DecisionCardModel = {
    id: `briefing:${leagueId}:${rosterId}`,
    lane: "lineup",
    scope: { leagueId, rosterId, assetIds: [] },
    action,
    outcome: `${league.direction_label} · ${league.league_name}`,
    timing:
      lineup?.title_window_label === "Peak Window"
        ? "Press the next weekly edge."
        : "Reassess before adding long-term cost.",
    urgency:
      lineup?.title_window_label === "Peak Window" ? "this_week" : "watch",
    confidence: {
      band,
      score: lineup?.title_window_composite,
      explanation:
        league.direction_reasoning ??
        league.direction_note ??
        "Direction is derived from the current roster and league evidence.",
    },
    acceptablePrice: null,
    risk: "A stale weekly source can turn a correct roster read into a bad immediate move.",
    invalidation:
      "A new injury, lineup role, league rule, or meaningful roster change invalidates this briefing.",
    evidence: [
      `Direction: ${league.direction_label} (${league.direction_read})`,
      `Primary weakness: ${league.primary_weakness}`,
      lineup
        ? `Lineup leverage: ${lineup.upgrade_leverage_point}`
        : "Lineup model has not produced a leverage point.",
    ],
    freshness: {
      state: league.last_ingest_at ? "fresh" : "unknown",
      domains: [],
    },
    cta: {
      label: "Open roster moves",
      destination: `/league/${leagueId}/roster-moves?rosterId=${rosterId}`,
    },
  }

  return (
    <section aria-labelledby="league-briefing-narrative" className="space-y-4">
      <div>
        <p className="font-label text-label-xs font-bold uppercase tracking-label text-primary">
          Decision narrative
        </p>
        <h2
          id="league-briefing-narrative"
          className="mt-2 font-headline text-2xl font-extrabold"
        >
          What are we, and what should we do next?
        </h2>
      </div>
      <DecisionCard card={card} />
    </section>
  )
}
