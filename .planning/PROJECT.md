# Dynasty Fantasy Football Front Office OS

## What This Is

A personal dynasty intelligence system for managing 1–3 Sleeper leagues. It ingests live league data and generates context-aware team evaluations, strategic direction recommendations, trade targeting, manager behavior profiles, dynamic pick valuations, and prospect research — all through a local web app dashboard. This is not a rankings calculator; it is a context engine that makes every recommendation relative to the specific league, roster, and manager environment it operates in.

## Core Value

The system must tell you — for each of your teams — what you are, what your best path is, who to trade with, what kind of deal to make, and whether the prospect or pick decision you're considering is actually sharp in this format and league.

## Requirements

### Validated

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
*Last updated: 2026-06-28 after the weekly projection, data-health, pre-scored trade package, executable CTA, and command-center acceptance tranche*
