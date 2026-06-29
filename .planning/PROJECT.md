# Dynasty Fantasy Football Front Office OS

## What This Is

A personal dynasty intelligence system for managing 1–3 Sleeper leagues. It ingests live league data and generates context-aware team evaluations, strategic direction recommendations, trade targeting, manager behavior profiles, dynamic pick valuations, and prospect research — all through a local web app dashboard. This is not a rankings calculator; it is a context engine that makes every recommendation relative to the specific league, roster, and manager environment it operates in.

## Core Value

The system must tell you — for each of your teams — what you are, what your best path is, who to trade with, what kind of deal to make, and whether the prospect or pick decision you're considering is actually sharp in this format and league.

## Requirements

### Validated

- League pages now include Trade History and Draft Grades screens: completed trades replay through current Trade Lab scoring with explicit at-time coverage, and stored rookie/startup selections get computed current-value grades plus at-time snapshot status.
- Trade Lab no longer renders the non-actionable primary-counterparty/deal-shape explainer beside the send/receive package builder.
- Trade Lab balance now separates consensus market value from app-adjusted value, with the seesaw using team fit, direction, insulation, production, scarcity, liquidity, and package concentration rather than consensus alone.
- App-wide decorative backlighting is removed from the global background, cards, primary buttons, active trade panels, popovers, and sheets while preserving borders and focus treatment.
- Trade Lab evaluations now include an adjusted trade-balance seesaw that discounts loose end-of-bench package pieces, so bulk depth does not equal elite value even when raw market totals match.
- Trade Lab now preserves full top-move trade CTA query params even when the router parses numeric-looking ids, and older name-only trade links resolve the target player into the appropriate send/receive side.
- Waiver FAAB ranges now cap non-starter stash bids when the roster already has a strong same-position anchor or the candidate is blocked by a better same-team positional player, preventing Theo Johnson-style TE depth from commanding priority FAAB behind Loveland.
- Valuation and trade logic now share a positional context model that accounts for league lineup demand, TEP/superflex settings, replacement baselines, tier-cliff scarcity, and roster surplus/deficit, so elite scarce assets require a roster-improving return while discounted same-position QB edges remain actionable.
- Command-center filter, league, and recompute controls now bottom-align so their visible boxes sit evenly in the Top Moves header.
- Command-center Top Moves hides start/sit cards by default behind an Include start/sit filter, and waiver/Edge Radar recommendations now respect Sleeper position caps such as AMG's QB limit.
- Command-center Top Moves now loads the selected league's action queue through the league-specific actions endpoint, with a compact league selector instead of a mixed cross-league list.
- Command-center Top Moves rows now use a restrained local shadow instead of the heavier shared panel glow.
- Command-center readiness lane counts stay out of the landing summary, so fresh data leaves no unexplained status row and stale warnings remain the only health chrome.
- Command-center Top Moves now render as compact expandable cards, and the data-health row omits a fresh-state flag when no stale domains need attention.
- Command-center stale refresh actions now update the freshness ledger when waiver boards are recomputed or market baselines are refreshed, so successful refreshes clear stale badges.
- League refresh now rebuilds the full local Edge Radar stack: team context, dense player metadata freshness, player values/trends, waiver recommendation caches, manager profiles, and snapshots, so Opportunity Feed and Command Center sessions read fresh side tables after one refresh.
- Weekly start/sit Command Center actions now require roster-legal lineup-slot swaps, reject NFL free-agent/no-game bench starters, and distinguish missing rookie stat samples from true zero-point projections.
- Command-center landing chrome is now compact, stale refresh actions are consolidated into one queued button, and Edge Radar ranks cheap candidates before enriching only the visible winners so Top Moves loads quickly.
- Command-center Edge Radar trade cards now suppress sell recommendations unless the player is actually on the selected portfolio roster, while still allowing opponent buy targets and deduplicating repeated Edge Radar action IDs and repeated player/signal cards before rendering.
- Edge Radar now exists as an internal backend discovery layer that ranks buy low, buy high, sell high, sell low, and waiver pickup signals by normalized model-vs-market delta, enriches player signals with similar-player outcome evidence from age/team/system/coach metadata when available, and feeds discoveries into Command Center actions instead of adding a competing frontend destination.
- League-page refresh now runs an incremental Sleeper ingest instead of freezing the current cached state, so manual refreshes rebuild analytics and write a fresh snapshot before the UI reloads.
- Multi-team trade evaluator reroutes and package builder outputs now use third-party sidecar evaluations to explain offers for every participant in the deal, not only the primary counterparty.
- Snapshot comparison membership is derived from `rosters.players`, so adds and departures still surface when player valuation rows lag behind roster ingestion.
- League drill-in now has a Player Rankings tab backed by `/dashboard/league/{league_id}/player-rankings`, showing model/market-ranked players with each player owner inline.
- Rookie-board cards and roster hygiene rows now surface live model-vs-market gaps from the shared recommendation-card market-gap engine after FantasyCalc ADP refreshes.
- DuckDB request handling now opens request-scoped file connections instead of sharing one global connection across FastAPI worker threads, preventing concurrent UI requests from corrupting pending query state.
- The 2026-06-26 UI rubric audit is recorded in `.planning/UI-RUBRIC-AUDIT-2026-06-26.md`, including the fixed mobile dashboard issue and remaining Opportunity Feed performance finding.
- The TMCP UI remediation pass now bounds Opportunity Feed similarity enrichment, adds a frontend request timeout/error path, and hides React Query Devtools on mobile so the feed settles and mobile content is unobstructed.
- The Opportunity Feed now has a ranked, scannable visual treatment with route-level signal totals, top-impact context, and stronger per-card rank/action/impact hierarchy.
- The league briefing header now separates command actions, primary navigation, and secondary league tools instead of rendering every destination as equal-weight oversized buttons.
- The app-wide UI remediation pass now caps Player Rankings rendering, compacts league subroute briefing chrome, demotes unavailable Startup navigation, removes nonfunctional global header utilities, and fixes known React console warning sources.
- The dashboard now opens with a cross-league command center backed by `/actions/command-center`, waiver cards include add/drop/FAAB guidance, opportunity ranking prioritizes actionable roster context over raw ADP gaps, and the refreshed DuckDB request policy removes mixed read-only/write connection failures.
- Weekly edge now has a first-class `/weekly/league/{league_id}/{roster_id}/edge` API and league-overview panel that turns recent public weekly stats, injury/status metadata, lineup gaps, and freshness tags into start/sit and lineup-upgrade actions; command-center trade cards now include suggested package shape and portfolio rows rank exposure by sell/hedge/monitor urgency.
- Weekly context can now be explicitly refreshed through `/weekly/league/{league_id}/refresh-context`, stores nflverse/nflreadpy schedule opponent context in DuckDB, marks injuries/usage/schedule/stats freshness domains, and surfaces matchup/usage notes inside weekly edge cards.
- Command-center trade actions now build from real roster assets and manager pitch evidence, then deep-link Trade Lab with concrete send/receive player params instead of generic package placeholders.
- The oversized league overview and trade route files were split into focused league/trade components and route helper modules while preserving route hydration and evaluator behavior.
- Command-center trade package construction now lives in a dedicated trade suggestion builder, and the Trade Lab route hydration/search parsing lives in route helper modules so both source files stay below local size gates.
- Weekly edge now scores start/sit moves with projection, availability, matchup, and opponent-position environment context; the command center shows data-health freshness, executable weekly/portfolio CTAs, and pre-scored trade packages with top-five action acceptance coverage.
- Player values now persist `trend_result` into recommendation cards, opportunity-feed trend computation is batched with bounded similar-player enrichment, and the feed exposes degraded-state metadata with a clearer frontend fallback.
- Browser/route smoke coverage now lives in `frontend/scripts/browserSmoke.mjs` with `pnpm browser:smoke` and `pnpm routes:smoke`, Playwright is a frontend dev dependency, and stale command-center freshness warnings now include executable refresh actions.
- Weekly-edge command links now highlight their exact start/sit or position-gap target, portfolio links highlight the target exposure row, weekly signals include bye/depth-context notes, opportunity similarity failures degrade to partial feed responses, and test schema setup is split out of oversized `conftest.py`.
- Command-center weekly actions now expose sit-player availability, projection, stale-domain, usage, matchup, and role evidence; cached waiver actions now inspect weekly lineup gaps so immediate starter adds that patch a title-lineup hole are promoted to today with explicit lineup-gap evidence.
- Buy-window command actions now inspect the user's weekly lineup gaps, so trade recommendations that solve a current starter hole include the gap evidence, stale weekly domains, and still deep-link into a prefilled Trade Lab package.
- Portfolio command actions now inspect player injury/status metadata, escalating repeated exposure on out or questionable players into hedge actions with availability evidence, injury freshness warnings, and portfolio drill-in CTAs.
- Command-center rookie pick actions now inspect active draft slots and Draft Room advice, surfacing take/trade-back guidance with prospect tier evidence, stale draft-data warnings, and direct Draft Room CTAs.
- Command-center weekly risk actions now surface bye/no-opponent starters even when no bench pivot exists, with replacement guidance, schedule freshness warnings, usage/role evidence, and direct Weekly Edge CTAs.
- Command-center manager exploit actions now require stronger evidence and build concrete Trade Lab packages with real send/receive assets, manager pitch framing, fairness evidence, and prefilled trade CTAs.
- Browser smoke discovery now retries dashboard summary during dev refresh warmup so route sweeps consistently include league, waiver, manager, and rookie-board routes when local league data is present.
- Command-center ranking now prefers ready execution inside equal urgency/confidence buckets, so prefilled manager offers and concrete next-click actions are not crowded out by generic market-monitor cards.
- Opportunity Feed scoring now boosts buy windows that solve active lineup gaps and dampens that weekly-fit boost when usage/stats/schedule/injury freshness is stale, adding plain-language lineup-gap and stale-data notes to the action rationale.
- Opportunity Feed items now expose structured weekly lineup-fit evidence, render lineup-gap and stale-weekly-data badges on cards, and include a route filter for opportunities that solve current lineup gaps.
- Command-center actions now require and render explicit acceptable-price and timing fields, so Top 5 cards consistently show action, price, timing, risk, evidence, stale-data warning, and next click.
- Command Center now returns and renders required move-lane coverage for start/sit, waiver, trade, rookie, portfolio, and manager angles, making missing decision lanes visible instead of silent.
- Manager-pitch trade packages now require roster-fit gating, so the Command Center skips offers that send protected scarce depth in premium formats for positions that are already sufficiently covered.

### Active

<!-- Phase 1: Core league ingest and team intelligence -->
- [ ] Ingest Sleeper league data via API (format, scoring, roster settings, lineup config, superflex/TEP/premium flags)
- [ ] Ingest rosters, standings, picks, points for/against per league
- [ ] Store league-specific settings and allow manual corrections universally
- [ ] Generate team scorecard with sub-scores (win-now, future value, depth, pick capital, flexibility, fragility, age risk, liquidity, positional insulation)
- [ ] Detect and recommend primary team direction with confidence score, reasoning, and alternate viable directions
- [ ] Produce player values adjusted for league format and team direction (not one opaque number)
- [ ] Dashboard: league cards, direction labels, top 3 action items, value risers/fallers, cross-league exposure alerts
- [ ] Save league snapshots and support multiple leagues in one account

<!-- Phase 2: Trade intelligence and manager dossiers -->
- [ ] Ingest trade and transaction history from Sleeper
- [ ] Build manager dossier per leaguemate (trade tendencies, overpay patterns, exploitability score, recommended pitch angles)
- [ ] Trade evaluator scoring market fairness, roster fit, direction fit, timing, insulation, liquidity, exploit quality
- [ ] Trade pathing: surface reroute paths, better targets, package alternatives, and pitch notes per manager
- [ ] Package builder with fair range, best version, and manager-specific opening offers

<!-- Phase 3: Dynamic pick engine and rookie workflow -->
- [ ] Dynamic pick valuation adjusted for class strength, standings, calendar timing, league demand, and active rebuilders
- [ ] Rookie board with format-aware ranks, tiers, and roster-fit overlays
- [ ] Pick timing recommendations (sell now vs. hold vs. use on the clock)
- [ ] Draft room view: best in abstract, best for this roster, best relative to your league's draft tendencies

<!-- Phase 4: Historical prospect lab -->
- [ ] 10+ year historical prospect database with positional splits
- [ ] Position-specific feature models (QB, RB, WR, TE) using age, testing, production, market share, usage, draft capital
- [ ] Threshold analysis, hit-rate buckets, archetype clustering, and historical comps
- [ ] Backtested findings used to weight models — no hardcoded assumptions without validation
- [ ] Prospect output: tier, archetype, comps, risk band, overvalue/undervalue flags

<!-- Phase 5: Portfolio intelligence and memory -->
- [ ] Portfolio exposure dashboard: player exposure across leagues, correlated risk, overexposure flags
- [ ] Season-over-season snapshots for team comparison and value tracking
- [ ] Manager behavior trend persistence across seasons
- [ ] Recommendation retrospectives (were direction labels calibrated? did prospect tiers hit?)

### Out of Scope

- Automating trades or sending offers directly — personal tool, manual execution only
- Replacing film study — data and statistical signals only
- Public-facing product — single user, local deployment
- Perfectly predicting player outcomes — probabilistic ranges and confidence levels, not oracle claims
- Full custom formula / model weight authoring in v1 — system stays opinionated with manual overrides only
- Forcing a single universal ranking list as the main interface

## Context

- Platform: Sleeper (has a free, well-documented public API — no auth required for public league reads)
- Form factor: Local web app, served to browser — Python backend (data modeling, analysis engines) + React frontend (dashboard UI)
- Scale: 1–3 active dynasty leagues currently; architecture should support more without redesign
- Current workflow: Manual — no systematic framework for team direction, trade targeting, or prospect evaluation
- Dynasty format coverage: Must handle superflex, TEP, premium scoring, and non-standard lineup configs from day one since these materially affect valuations
- Design philosophy: Opinionated recommendations with visible sub-scores and confidence levels, not dashboards that stop at data display

## Constraints

- **Platform**: Sleeper API first — architect ingestion layer for additional platforms later without coupling analysis engines to platform specifics
- **Deployment**: Local only in v1 — no hosted backend, no auth system, no multi-user concerns
- **Model editability**: Core model weights not fully user-editable in v1 — manual correction and notes supported everywhere, deep formula authoring deferred
- **Data availability**: Some league data (full trade history, draft history) may be incomplete — manual fallback required for all data domains
- **False precision**: Uncertainty is real in dynasty evaluation — every recommendation must show confidence level and what could break the thesis

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Sleeper as first platform integration | Free public API, no OAuth complexity, large dynasty player base | — Pending |
| Python backend + React frontend | Python natural fit for data modeling, analytics, and multi-engine composition; React best for dashboard-heavy local web UI | — Pending |
| Six modular sub-engines (global baseline, league context, team direction, manager behavior, trade pathing, prospect research) | Keeps system composable and scalable; prevents one monolith from coupling unrelated analysis domains | — Pending |
| League-specific recommendations by default, portfolio layer opt-in | Prevents cross-league flattening of strategy while still tracking exposure | — Pending |
| Opinionated recommendations with visible sub-scores | System must not stop at dashboards — ranked recommendations with explanations are a first-class output | — Pending |

---
*Last updated: 2026-06-29 after adding league trade audit and draft grade screens*
