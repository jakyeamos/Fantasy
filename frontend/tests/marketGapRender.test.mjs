import assert from "node:assert/strict"
import { createElement } from "react"
import { renderToStaticMarkup } from "react-dom/server"
import { createServer } from "vite"

const buyLowGap = {
  market_rank: 12,
  model_rank: 4,
  market_value: 0.55,
  model_value: 0.82,
  gap_magnitude: 0.27,
  gap_direction: "model_above",
  gap_classification: "buy_low",
  explanation: "Model rates this asset higher the market by 0.27 normalized points.",
}

const rookie = {
  player_id: "rookie_wr",
  full_name: "Rookie WR",
  position: "WR",
  archetype_label: "Route Runner",
  risk_band: "Low",
  composite_score: 82,
  tier_number: 1,
  available_probability_by_slot: {},
  model_vs_market_gap: buyLowGap,
}

const hygieneSuggestion = {
  action_type: "shop",
  primary_player_ids: ["veteran_wr"],
  primary_player_names: ["Veteran WR"],
  target_player_id: null,
  target_player_name: null,
  counterparty_roster_id: null,
  counterparty_name: null,
  reasoning: "Shop the player while the market remains ahead of the model.",
  direction_fit_score: 0.78,
  timing_rationale: "Market signal is live after refresh.",
  packaging_rationale: null,
  player_context_flags: [],
  model_vs_market_gap: {
    ...buyLowGap,
    gap_direction: "model_below",
    gap_classification: "sell_high",
  },
}

const server = await createServer({
  configFile: new URL("../vite.config.ts", import.meta.url).pathname,
  server: { hmr: false, middlewareMode: true, ws: false },
  appType: "custom",
})

try {
  const { RookiePlayerCard } = await server.ssrLoadModule(
    "/src/components/rookie/RookiePlayerCard.tsx",
  )
  const { HygieneSuggestionRow } = await server.ssrLoadModule(
    "/src/components/hygiene/HygieneSuggestionRow.tsx",
  )

  const rookieMarkup = renderToStaticMarkup(createElement(RookiePlayerCard, { player: rookie }))
  assert.match(rookieMarkup, /Market Gap/)
  assert.match(rookieMarkup, /BUY LOW/)

  const hygieneMarkup = renderToStaticMarkup(
    createElement(HygieneSuggestionRow, {
      suggestion: hygieneSuggestion,
      leagueId: "league_x",
    }),
  )
  assert.match(hygieneMarkup, /SELL HIGH/)
  assert.match(hygieneMarkup, /Veteran WR/)
} finally {
  await server.close()
}
