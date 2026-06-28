import assert from "node:assert/strict"

import type { OpportunityFeedItem } from "../src/api/types"
import { filterOpportunityItems } from "../src/lib/opportunityFilters"

function item(
  playerId: string,
  weeklyFit: OpportunityFeedItem["weekly_fit"],
): OpportunityFeedItem {
  return {
    player_id: playerId,
    player_name: playerId,
    position: "WR",
    trend_label: "will_rise",
    trend_confidence: "HIGH",
    adp_gap: -24,
    suggested_action: "buy",
    availability: "opponent_roster",
    impact_score: 42,
    why_summary: "Buy signal",
    owned_in_leagues: [],
    similar_players: [],
    conflict_explanation: null,
    calendar_escalated: false,
    calendar_escalation_label: null,
    cta: null,
    weekly_fit: weeklyFit,
  }
}

const lineupFit = item("lineup_fit", {
  position: "WR",
  player_name: "Weak WR",
  gap_to_title_target: 14,
  is_stale: false,
  stale_domains: [],
})
const rawMarket = item("raw_market", null)

assert.deepEqual(
  filterOpportunityItems([lineupFit, rawMarket], {
    scopeFilter: "all",
    actionFilter: "all",
    highConfidenceOnly: false,
    leagueFilter: "all",
    includeSpeculative: false,
    lineupFitOnly: true,
  }).map((candidate) => candidate.player_id),
  ["lineup_fit"],
)
