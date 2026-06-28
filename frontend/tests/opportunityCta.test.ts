import assert from "node:assert/strict"

import type { OpportunityFeedItem } from "../src/api/types"
import { buildOpportunityCtaTarget } from "../src/lib/opportunityCta"

const baseItem: OpportunityFeedItem = {
  player_id: "player_1",
  player_name: "Player One",
  position: "WR",
  trend_label: "will_rise",
  trend_confidence: "HIGH",
  adp_gap: -32,
  suggested_action: "buy",
  availability: "opponent_roster",
  impact_score: 32,
  why_summary: "Buy signal",
  owned_in_leagues: [],
  similar_players: [],
  conflict_explanation: null,
  calendar_escalated: false,
  calendar_escalation_label: null,
  cta: null,
  weekly_fit: null,
}

assert.deepEqual(
  buildOpportunityCtaTarget({
    ...baseItem,
    cta: {
      label: "Build Buy Offer",
      destination: "trade_evaluator",
      league_id: "league_a",
      user_roster_id: 1,
      manager_roster_id: 2,
      target_player_roster_id: 2,
    },
  }),
  {
    kind: "trade_evaluator",
    label: "Build Buy Offer",
    search: {
      leagueId: "league_a",
      userRosterId: 1,
      counterpartyRosterId: 2,
      targetPlayerId: "player_1",
      targetPlayerName: "Player One",
      targetPlayerPosition: "WR",
      targetPlayerRosterId: 2,
    },
  },
)

assert.deepEqual(
  buildOpportunityCtaTarget({
    ...baseItem,
    suggested_action: "sell",
    cta: {
      label: "Shop in Trade Evaluator",
      destination: "trade_evaluator",
      league_id: "league_b",
      user_roster_id: 4,
      manager_roster_id: null,
      target_player_roster_id: 4,
    },
  }),
  {
    kind: "trade_evaluator",
    label: "Shop in Trade Evaluator",
    search: {
      leagueId: "league_b",
      userRosterId: 4,
      counterpartyRosterId: undefined,
      targetPlayerId: "player_1",
      targetPlayerName: "Player One",
      targetPlayerPosition: "WR",
      targetPlayerRosterId: 4,
    },
  },
)

assert.deepEqual(
  buildOpportunityCtaTarget({
    ...baseItem,
    cta: {
      label: "View Manager",
      destination: "manager_dossier",
      league_id: "league_a",
      user_roster_id: 1,
      manager_roster_id: 3,
      target_player_roster_id: 3,
    },
  }),
  {
    kind: "manager_dossier",
    label: "View Manager",
    params: {
      leagueId: "league_a",
      managerId: "3",
    },
  },
)

assert.deepEqual(
  buildOpportunityCtaTarget({
    ...baseItem,
    cta: {
      label: "View Rankings",
      destination: "player_rankings",
      league_id: "league_c",
      user_roster_id: 5,
      manager_roster_id: null,
      target_player_roster_id: null,
    },
  }),
  {
    kind: "player_rankings",
    label: "View Rankings",
    params: {
      leagueId: "league_c",
    },
  },
)
