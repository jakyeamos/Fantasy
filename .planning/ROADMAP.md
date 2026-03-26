# Roadmap: Dynasty Fantasy Football Front Office OS

## Overview

This project builds a personal dynasty intelligence system in sixteen focused phases. Phases 1-3 deliver the core ingestion pipeline, team intelligence engines, and dashboard -- the system's foundational thesis. A hard gate between Phase 3 and Phase 4 requires manual direction label validation against all active leagues before trade and manager intelligence is built on top of it. Phases 4-5 add counterparty intelligence and trade evaluation. Phases 6-7 deliver the dynamic pick engine and rookie tooling. Phase 8 builds the historical prospect lab with backtested models. Phase 9 closes the trust loop with portfolio-level exposure tracking and recommendation retrospectives. Phases 10-16 add fantasy-specific enhancements: draft order accuracy, roster and lineup intelligence, manager market profiling, context awareness, format trust infrastructure, waiver and startup workflows, and thesis-level portfolio expansion.

## Phases

**Phase Numbering:**
- Integer phases (1-16): Planned milestone work
- Decimal phases (e.g., 3.1): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Sleeper Ingestion** - Stack scaffold, Sleeper adapter, full data ingest pipeline with health checks
- [x] **Phase 2: Team Intelligence** - Team scorecard, direction detection, player valuation engines
- [x] **Phase 3: Core Dashboard** - League card UI, dashboard views, snapshot table wire-in
- [x] **Phase 4: Manager Profiling** - Leaguemate dossiers, exploitability scoring, pitch angle generation
- [x] **Phase 5: Trade Intelligence** - Trade evaluator, reroute pathing, package builder
- [x] **Phase 6: Dynamic Pick Valuation** - Standings-aware pick engine, demand signals, timing recommendations
- [x] **Phase 7: Rookie Board & Draft Room** - Format-aware rookie tiers, roster-fit overlays, draft room view
- [ ] **Phase 8: Historical Prospect Lab** - 10+ year database, backtested position models, archetype clustering
- [ ] **Phase 9: Portfolio & Retrospectives** - Cross-league exposure, season-over-season snapshots, retrospective grading
- [ ] **Phase 10: Pick Accuracy & Draft Order** - Draft order rules engine, format-aware pick slot projections (FS-01)
- [x] **Phase 11: Roster & Lineup Intelligence** - Optimal lineup calculator, title-window score, roster management layer (FS-02, FS-04) (completed 2026-03-25)
- [ ] **Phase 12: Manager Rookie & Pick Profiles** - Rookie-draft behavior mining, pick-premium scoring, profile-aware suggestions (FS-06)
- [ ] **Phase 13: Context Awareness** - Dynasty calendar state, NFL context freshness, time-aware recommendations (FS-03, FS-08)
- [ ] **Phase 14: Trust Infrastructure** - League rule support matrix, unsupported-format flagging, fallback behavior (FS-07)
- [ ] **Phase 15: Waiver & Startup Workflows** - FAAB/waiver intelligence, startup draft mode, orphan intake checklist (FS-05, FS-09)
- [ ] **Phase 16: Portfolio Thesis Expansion** - Thesis-level exposure tracking, concentration flags, diversification suggestions (FS-10)

## Phase Details

### Phase 1: Sleeper Ingestion
**Goal**: The system reliably ingests all Sleeper league data the analysis engines require, surfaces explicit data gaps, and allows manual correction of any ingested value
**Depends on**: Nothing (first phase)
**Requirements**: INGEST-01, INGEST-02, INGEST-03, INGEST-04, INGEST-05, INGEST-06, INGEST-07, INGEST-08
**Success Criteria** (what must be TRUE):
  1. User can connect a league by ID and see all format settings (scoring, roster config, superflex/TEP/premium flags) populated in the UI
  2. Rosters, standings, picks, trade history, and transaction history are ingested and queryable for all connected leagues
  3. Dashboard shows a data freshness status per league with explicit gaps called out (e.g., "trade history incomplete before 2023")
  4. User can manually correct any ingested data point and see the correction persist across sessions
  5. The ingest pipeline runs against incomplete or partial Sleeper API responses without crashing -- null gaps are surfaced, not silently dropped
**Plans**: 6 plans

**Open question resolved:** Scoring history uses nfl_data_py (not Sleeper's deprecated player stats endpoint). Fantasy points reconstructed from raw stat lines using each league's actual scoring_settings. 10+ years of data ingested in Phase 1 to seed Phase 8's Historical Prospect Lab.

**Open question resolved:** Global Asset Baseline seeded from two sources: ADP signals (FantasyPros dynasty ADP CSV) + nfl_data_py scoring reconstruction. Baseline is foundation-only in Phase 1; Phase 2 applies league-specific adjustments on top.

Plans:
- [x] 01-00-PLAN.md -- Project scaffold: FastAPI skeleton, DuckDB schema + Alembic migrations, test stubs
- [x] 01-01-PLAN.md -- SleeperMapper adapter: domain models (LeagueSettings, RosterSnapshot, TradedPick, StandingRow, TransactionRecord)
- [x] 01-02-PLAN.md -- Repository layer: LeagueRepo DuckDB upserts + NflDataPyLoader with fantasy point reconstruction
- [x] 01-03-PLAN.md -- SleeperClient (httpx + tenacity) + IngestService orchestration with all-weeks transaction loop
- [x] 01-04-PLAN.md -- OverrideService (corrections CRUD) + FastAPI routers (ingest, corrections) wired into main.py
- [x] 01-05-PLAN.md -- GapDetector + health endpoint + ADP baseline loader + human-verify checkpoint

---

### Phase 2: Team Intelligence
**Goal**: The system generates team scorecards with decomposed sub-scores, detects team direction with confidence and reasoning, and produces player values adjusted for league format and team direction
**Depends on**: Phase 1
**Requirements**: TEAM-01, TEAM-02, TEAM-03, TEAM-04, TEAM-05, PLAY-01, PLAY-02, PLAY-03, PLAY-04
**Success Criteria** (what must be TRUE):
  1. User can view a team scorecard showing all 9 sub-scores (win-now, future value, depth, pick capital, flexibility, fragility, age risk, liquidity, positional insulation) with no sub-score displayed as a single opaque integer
  2. System recommends a primary direction from 8 options with a confidence score, reasoning, and 2+ alternate viable directions for every team
  3. Direction recommendation includes what would materially alter the label and which move types are approved or discouraged
  4. User can view any player across 5 value lenses (production, market, insulation, team-fit, direction-specific) with the active team's direction weighting applied
  5. Ranked move recommendations per team are visible and reflect the current direction label
**Plans**: 5 plans

Plans:
- [x] 02-00-PLAN.md -- Intelligence package scaffold: output table migrations, constants, Pydantic models, test stubs
- [x] 02-01-PLAN.md -- ScorecardEngine: 9-dimension scoring, normalization, corrections application
- [x] 02-02-PLAN.md -- DirectionEngine: weighted dot-product classification, confidence, alternates, delta, ranked moves
- [x] 02-03-PLAN.md -- ValuationEngine: 12 components, 5 lenses, PPR/superflex/TEP adjustments, direction reweighting
- [x] 02-04-PLAN.md -- IntelligenceService orchestration + FastAPI /intelligence router wired into main.py

---

### Phase 3: Core Dashboard
**Goal**: The dashboard surfaces direction labels, value changes, cross-league exposure, and exploit windows per connected league -- and the snapshot table is wired in so early data is never lost
**Depends on**: Phase 2
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, PORT-01
**Success Criteria** (what must be TRUE):
  1. User sees a card per connected league on load showing direction label, confidence level, and primary team weakness -- visible without scrolling or expanding sub-panels
  2. Dashboard displays biggest value risers and fallers across all connected leagues
  3. Dashboard alerts fire for players owned across 2+ leagues with concentration risk flags
  4. Dashboard surfaces leaguemates currently showing behavioral triggers (losing trades, positional thinness, recent panic moves)
  5. League snapshots are saved automatically at scheduled intervals and on user trigger -- early snapshots cannot be recovered retroactively, so this must be live before Phase 4
**Plans**: 3 plans

**HARD GATE -- Phase 3 exit:** Before Phase 4 begins, direction labels must be manually reviewed and confirmed against all active leagues. If a direction label is materially wrong (e.g., a clear rebuild labeled as a contender), Phase 4 and Phase 5 must not proceed until the engine is corrected. This gate is not optional.

Plans:
- [x] 03-01-PLAN.md -- Backend: snapshot migration, SnapshotService, dashboard + snapshot routers, post-ingest hook
- [x] 03-02-PLAN.md -- Frontend scaffold: Vite + React 19 + TanStack Router/Query + shadcn/ui init + route shells + API queries
- [x] 03-03-PLAN.md -- Frontend views: LeagueCard grid, drill-in with risers/fallers + exploit windows + snapshot controls + human-verify

**Known gap (DASH-03 / PORT-03):** Cross-league concentration risk alerts not implemented in dashboard. Behavioral exploit windows are present; player ownership concentration surface deferred to Phase 9 (PORT-03).

---

### Phase 4: Manager Profiling
**Goal**: The system generates a dossier per leaguemate with evidence-backed exploitability scoring, suppressing or labeling LOW confidence where trade evidence is insufficient
**Depends on**: Phase 3 (direction gate cleared)
**Requirements**: MGR-01, MGR-02, MGR-03, MGR-04
**Success Criteria** (what must be TRUE):
  1. User can view a dossier per leaguemate showing roster summary, likely direction, positional needs, trade history trends, preferred asset types, and least-valued asset types
  2. Exploitability score is displayed with evidence count prominently; any dossier with fewer than 10 trades in evidence shows a LOW confidence label -- the threshold is a named constant, not a magic number
  3. Recommended pitch angles per manager are surfaced with deal archetypes likely to be accepted and structures to avoid
  4. Each dossier distinguishes exploitation type: value-loss trader, timing-error trader, directionally-incoherent trader, or archetype-specific overpayer
**Plans**: 4 plans

Plans:
- [x] 04-01-PLAN.md -- Backend foundation: profiling constants, Pydantic models, Alembic migration 006, ProfilingRepo
- [x] 04-02-PLAN.md -- Backend engine + router: ProfilingEngine (exploitation classification, scoring, pitch angles), FastAPI router, unit tests
- [x] 04-03-PLAN.md -- Frontend managers list: shadcn install (tabs/table/alert), ManagerListRow, managers route, Phase 3 ExploitWindowPanel link update
- [x] 04-04-PLAN.md -- Frontend dossier: DossierPage with tabs, Overview/TradeHistory/PitchAngles tab components, human-verify checkpoint

---

### Phase 5: Trade Intelligence
**Goal**: The system evaluates any proposed trade across 7 scored dimensions, surfaces reroute paths and package alternatives, and distinguishes market-fair trades from strategically advancing ones
**Depends on**: Phase 4
**Requirements**: TRADE-01, TRADE-02, TRADE-03, TRADE-04
**Success Criteria** (what must be TRUE):
  1. User can input any proposed trade and see scores for all 7 dimensions (market fairness, roster fit, direction fit, timing quality, insulation gain/loss, liquidity gain/loss, manager exploit quality) each with a confidence level
  2. System surfaces at least one reroute path per trade evaluation: a better target for the same asset, a pick-based version, or a tier-down option
  3. Package builder generates a fair range, best version, and manager-specific opening offer for any desired acquisition
  4. System explicitly distinguishes a market-fair but strategically mediocre trade from one that advances the team's direction label
**Plans**: 4 plans

Plans:
- [x] 05-01-PLAN.md -- Backend foundation: trade constants, Pydantic models (TradeRequest/TradeEvaluation/DimensionScore), TradeRepo for Phase 2/4 data reads
- [x] 05-02-PLAN.md -- Backend engines + router: TradeEngine (7-dimension scoring), RerouteEngine, PackageBuilder, FastAPI /trade router, unit tests
- [x] 05-03-PLAN.md -- Frontend evaluator core: shadcn installs, TypeScript types, TradeInputPanel, EvaluationOutputPanel, StrategicDistinctionBanner, DimensionScoreRow, /trades route
- [x] 05-04-PLAN.md -- Frontend completion: RerouteSheet, PackageBuilderPanel, entry point buttons on league drill-in + manager dossier, human-verify checkpoint

**Known gap:** Multi-team third-party trade legs are parsed and passed through the API but TradeEngine does not score them. UI shows a note acknowledging this. Deferred to Phase 9.

**Known gap:** Trade evaluator only surfaces picks for the counterparty — their rostered players are not available to select as assets. Fix required in the counterparty asset lookup. Deferred to Phase 9.

---

### Phase 6: Dynamic Pick Valuation
**Goal**: Pick values are computed dynamically from current standings, draft proximity, class strength, and league-specific rebuilder count -- with timing recommendations per pick
**Depends on**: Phase 5
**Requirements**: PICK-01, PICK-02, PICK-03
**Success Criteria** (what must be TRUE):
  1. Pick values update when standings change -- a team going on a losing streak changes that pick's value at evaluation time, not at a fixed schedule
  2. Pick values reflect manager-specific demand signals within the league (a known rebuilder wanting early picks is priced in)
  3. Each pick shows a timing recommendation (sell now / hold until rookie fever / use on the clock) with reasoning tied to current standing trajectory and class strength perception
**Plans**: 4 plans

**Research complete:** Dynasty pick valuation algorithm researched -- standings-to-slot projection, calendar timing cycle, rebuilder demand adjustment, and per-manager demand factor all specified with community-verified methodology.

Plans:
- [x] 06-01-PLAN.md -- Backend foundation: picks package with constants, models (PickValue, PickValuationContext with Phase 7 hook), PickRepo, Alembic migration 009, test stubs
- [x] 06-02-PLAN.md -- PickEngine TDD: four-factor formula (standings slot, calendar timing, class strength hook, demand adjustment), timing recommendations, edge cases
- [x] 06-03-PLAN.md -- FastAPI /picks router, main.py registration, Phase 5 TradeRepo pick value redirect to PickEngine, integration tests
- [x] 06-04-PLAN.md -- Frontend: TimingBadge, AssetChip pick variant extension, PickValueSummaryRow for trade evaluator, LeaguePickList with recompute, human-verify checkpoint

---

### Phase 7: Rookie Board & Draft Room
**Goal**: The system produces a format-aware rookie board with tiered rankings and slot availability highlighting, and the draft room view answers three key questions: best player in abstract, league draft tendencies, and whether trading the pick is the superior play
**Depends on**: Phase 6
**Requirements**: PICK-04, PICK-05, PICK-06
**Success Criteria** (what must be TRUE):
  1. Rookie board displays tiers, archetype labels, and risk bands adjusted for the active league's scoring format and lineup requirements
  2. User can highlight players likely available at a given pick slot on the rookie board (roster-fit reranking descoped per D-05; replaced by slot availability filtering per D-06)
  3. Draft room view answers: best in abstract, best relative to this league's draft tendencies, and when trading the pick is the superior play (3 questions per D-07)
**Plans**: 4 plans

Plans:
- [x] 07-01-PLAN.md -- Backend foundation: rookie package with constants, Pydantic models, RookieRepo, Alembic migration 010 (rookie_board_cache + league_draft_tendencies tables)
- [x] 07-02-PLAN.md -- RookieEngine: format-aware scoring, gap-based tier assignment, archetype labels, risk bands, class strength signal, slot availability estimation, unit tests
- [x] 07-03-PLAN.md -- Draft room engine (compute_draft_room, trade verdict, tendency analysis), FastAPI /rookie-board + /draft-room routers, Phase 6 class_strength hook wiring
- [x] 07-04-PLAN.md -- Frontend: TypeScript types, TanStack Query hooks, RookiePlayerCard, TierDivider, TierGroup, VerdictBanner, TendencyWarningList, two new routes, league drill-in nav, human-verify checkpoint

---

### Phase 8: Historical Prospect Lab
**Goal**: The system maintains a backtested historical prospect database and generates evidence-backed tier assignments, archetype clustering, and historical comps per prospect
**Depends on**: Phase 7
**Requirements**: PROS-01, PROS-02, PROS-03, PROS-04, PROS-05
**Success Criteria** (what must be TRUE):
  1. Historical prospect database covers 10+ years with positional splits; user can query it from the UI
  2. Position-specific feature models exist for QB, RB, WR, and TE with weights derived from backtested hit rates, not hardcoded assumptions
  3. Each current prospect shows: tier, archetype label, historical comps, hit-rate bucket, and risk band
  4. System flags why a prospect is overvalued or undervalued by the current market relative to historical positional evidence -- the flag includes the specific divergence
**Plans**: 5 plans

**Research complete:** ML model selection (scikit-learn Random Forest for RB/WR/TE, Logistic Regression for QB), nflreadpy ETL pipeline, walk-forward time-based backtesting, K-means archetype clustering, and comp finding methodology all specified.

Plans:
- [ ] 08-01-PLAN.md -- Data foundation: prospects package scaffold, constants, Pydantic models, DuckDB migration, ProspectRepo, NflReadPyLoader, FeatureBuilder with outcome labeling
- [ ] 08-02-PLAN.md -- ML engines: HitClassifier (three-bucket labeling), ProspectModel (position-specific walk-forward backtesting), ArchetypeClusterer (K-means)
- [ ] 08-03-PLAN.md -- CompFinder (historical comps by feature distance within ADP tier) + DivergenceEngine (over/undervalue flags with per-signal sub-flags)
- [ ] 08-04-PLAN.md -- CLI pipeline script (full model orchestration) + FastAPI /prospects router (model-outputs + comps endpoints) + main.py registration
- [ ] 08-05-PLAN.md -- Frontend: TypeScript types, TanStack Query hooks, RookiePlayerCard Phase 8 extensions (hit-rate badge, over/undervalue flag, historical comps), sort controls, human-verify checkpoint

---

### Phase 9: Portfolio & Retrospectives
**Goal**: The system tracks cross-league player exposure and portfolio-level risk, enables season-over-season comparison against historical snapshots, and grades past direction labels and prospect tiers against actual outcomes
**Depends on**: Phase 8
**Requirements**: PORT-02, PORT-03, PORT-04, PORT-05, PORT-06
**Success Criteria** (what must be TRUE):
  1. User can view player ownership across all connected leagues with concentration exposure flags (owned in 3+ leagues, correlated injury risk)
  2. User can compare any team's current state to a historical snapshot -- scorecard, direction label, player values, and pick capital all comparable side by side
  3. System grades past direction labels against actual season outcomes and surfaces calibration quality (was "true contender" calibrated?)
  4. System grades past prospect tier assignments against NFL outcomes and surfaces model accuracy per position and tier
**Plans**: 5 plans

Plans:
- [ ] 09-01-PLAN.md -- Backend foundation: portfolio package scaffold, constants, models, PortfolioRepo, migration 007, SnapshotService capital_score patch
- [ ] 09-02-PLAN.md -- Backend: SnapshotDiffEngine (anchor detection, delta-forward diff), snapshot diff router, main.py registration
- [ ] 09-03-PLAN.md -- Backend: PortfolioEngine (hedge recs, correlated risk), RetroEngine (direction + prospect grading), portfolio router
- [ ] 09-04-PLAN.md -- Frontend: Portfolio page with ExposureMatrix, CorrelatedRiskSection, health indicator, nav link, TypeScript types, query hooks
- [ ] 09-05-PLAN.md -- Frontend: SnapshotComparisonSheet, AnchorSelector, SnapshotDiffView, league drill-in integration, human-verify checkpoint

---

---

### Phase 10: Pick Accuracy & Draft Order
**Goal**: Pick values and projected draft slots are computed from the actual draft-order rules each league uses, not a universal inverse-standings assumption
**Depends on**: Phase 9
**Requirements**: FS-01
**Success Criteria** (what must be TRUE):
  1. Each connected league has an explicit `LeagueDraftOrderRule` capturing order basis, lottery configuration, playoff-team ordering, tiebreakers, and consolation exceptions
  2. Pick valuations and projected draft-slot calculations use the stored rule set, not inverse standings by default
  3. Every surface that shows a projected pick value cites the active draft-order rule explanation
  4. A per-league manual rule editor covers settings Sleeper does not expose via API
  5. Regression fixtures pass for: inverse standings, max PF for non-playoff teams, lottery top four, and playoff teams ordered by finish
**Plans**: 4 plans

Plans:
- [ ] 10-01-PLAN.md -- Backend foundation: enums, LeagueDraftOrderRule model, migration 012, triple-managed schema, PickRepo CRUD, API endpoints
- [ ] 10-02-PLAN.md -- Pick engine: rule-dispatching expected_draft_slot, blocked state, citation rendering, batch optimization
- [ ] 10-03-PLAN.md -- Backend regression tests: inverse standings, max PF, tiebreaker, playoff ordering fixtures + integration tests
- [ ] 10-04-PLAN.md -- Frontend: DraftOrderRuleForm, RuleCitation component, pick surface updates, blocked state rendering

---

### Phase 11: Roster & Lineup Intelligence
**Goal**: The system distinguishes a strong roster in abstract from a lineup that can actually win in the current format, and surfaces actionable low-level roster moves below the trade layer
**Depends on**: Phase 10
**Requirements**: FS-02, FS-04
**Success Criteria** (what must be TRUE):
  1. An optimal-starting-lineup calculator uses each league's real lineup constraints and scores starter strength by position against replacement-level baselines
  2. A title-window score weights elite starter ceiling, lineup stability, and playoff-usable depth -- visible on each team screen
  3. Team direction labels and trade recommendations can cite lineup-level reasons, not just aggregate roster value
  4. Every team screen includes a roster-hygiene panel with stash, cut, move-to-taxi, and consolidation suggestions
  5. Taxi eligibility, IR occupancy, and manual exceptions are modeled per league
**Plans**: 5 plans

Plans:
- [x] 11-01-PLAN.md -- Backend foundation: lineup package, models, constants, migration 014, LineupRepo, triple-write schema
- [x] 11-02-PLAN.md -- Engines: LineupEngine (replacement-level, title-window), HygieneEngine (consolidation/cut/stash/taxi), IntelligenceService wiring, API routers, unit + integration tests
- [x] 11-03-PLAN.md -- Frontend types, query hooks, TitleWindowPanel, LineupStrengthCard, TaxiIRSlotSummary, TaxiConfigForm
- [x] 11-04-PLAN.md -- Frontend hygiene: RosterHygienePanel, HygieneSuggestionRow, route wiring into league team screen, human-verify checkpoint
- [ ] 11-05-PLAN.md -- Gap closure: manual exceptions field (model/schema/repo/API/frontend) + FS-02/FS-04 defined in REQUIREMENTS.md

---

### Phase 12: Manager Rookie & Pick Profiles
**Goal**: Manager dossiers extend into rookie-draft and pick-market behavior, enabling the trade and draft views to surface which counterparty is most likely to buy a given prospect or pick profile
**Depends on**: Phase 11
**Requirements**: FS-06
**Success Criteria** (what must be TRUE):
  1. Historical rookie-draft selections are mined for positional preference, early-vs-late aggression, and repeated archetype bets per manager
  2. Each manager has a pick-premium score (willingness to pay for early firsts, second-round darts, draft-day trade-ups)
  3. Package builder, reroute suggestions, and draft-room warnings incorporate rookie/pick-market tendencies
  4. Low-confidence suppression is applied when historical rookie-draft evidence is too thin
**Plans**: 5 plans

Plans:
- [ ] 12-01-PLAN.md -- Backend foundation: rookie_pick package, constants, models, RookiePickRepo, migration 015, schema triple-write, SleeperClient/mapper extension
- [ ] 12-02-PLAN.md -- RookiePickProfileEngine, ManagerProfile extension, profiling router updates, on-demand draft-pick ingest endpoint
- [ ] 12-03-PLAN.md -- Trade model extension (picks_buyer reroute type), RerouteEngine picks_buyer logic, PackageBuilder pick-premium integration, draft room warnings
- [ ] 12-04-PLAN.md -- Frontend dossier: RookiePickMarketCard, DossierDraftPicksTab, 4th tab conditional rendering
- [ ] 12-05-PLAN.md -- Frontend list + draft room: Picks Buyer badge in ManagerListRow, manager_tendency type extension, human-verify checkpoint

---

### Phase 13: Context Awareness
**Goal**: Recommendations change intentionally with the dynasty calendar and react to football reality shifts -- calendar state and NFL context freshness are explicit, visible, and attributable
**Depends on**: Phase 12
**Requirements**: FS-03, FS-08
**Success Criteria** (what must be TRUE):
  1. A calendar-state service auto-selects the current dynasty state (startup, preseason, early season, trade deadline, playoffs, rookie fever, post-combine, post-NFL Draft) and allows manual override
  2. Trade, pick, rookie-board, and dashboard recommendation text cites the active calendar state
  3. The same asset demonstrably receives different guidance in different calendar windows (test-verified)
  4. Freshness domains (injuries, depth-chart changes, free agency, combine, draft capital, landing spots) are tagged on recommendation surfaces with stale-state warnings
  5. Major NFL events (Draft, major injuries) trigger an intentional refresh of affected outputs
**Plans**: 0 plans

---

### Phase 14: Trust Infrastructure
**Goal**: No connected league silently receives high-confidence advice under rules the tool does not actually model
**Depends on**: Phase 13
**Requirements**: FS-07
**Success Criteria** (what must be TRUE):
  1. A league scanner flags formats that materially change dynasty value: IDP, devy, salary cap, contracts, best ball, empire, median wins, points per first down, return-yard scoring, and TE-premium variants
  2. Each league rule is classified as supported, partially supported, or unsupported
  3. Partially supported rules require manual acknowledgment where recommendations may be distorted
  4. A league-level warning banner appears when a rule set falls outside the trusted support matrix
  5. Fallback behavior is defined and applied for every partially supported rule
**Plans**: 0 plans

---

### Phase 15: Waiver & Startup Workflows
**Goal**: Waivers and new-team scenarios are first-class dynasty workflows, not afterthoughts
**Depends on**: Phase 14
**Requirements**: FS-05, FS-09
**Success Criteria** (what must be TRUE):
  1. The app surfaces who to add on waivers and a bid range, or explicitly states a player is only worth a free post-waiver claim
  2. Bid-range suggestions are tied to team direction, remaining FAAB budget, and urgency
  3. A startup-draft mode provides startup pick valuation, trade-up/down heuristics, and direction-aware build templates
  4. An orphan intake checklist evaluates age curve, pick capital, dead roster spots, lineup viability, and liquidation options
  5. A newly connected team or orphan roster receives a clear first-pass 30-day action plan
**Plans**: 0 plans

---

### Phase 16: Portfolio Thesis Expansion
**Goal**: Portfolio analysis explains what football bets are overexposed across leagues, not just which players appear in multiple rosters
**Depends on**: Phase 15
**Requirements**: FS-10
**Success Criteria** (what must be TRUE):
  1. Exposure tracking extends from player names to rookie classes, archetypes, age buckets, NFL teams, offenses, and strategic labels
  2. Concentration flags surface thesis-level bets (too much of one rookie class, too many fragile contender rosters)
  3. Diversification suggestions recommend what kind of asset or direction would reduce overexposure
  4. Trade-impact previews show how a proposed move changes thesis exposure, not just player overlap
**Plans**: 0 plans

---

## Cross-Cutting Backlog

The items in `.planning/FANTASY-BACKLOG.md` have been sequenced into Phases 10-16 above. The backlog file is retained as the source-of-truth for the original task breakdowns and validation criteria.

---

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> [GATE] -> 4 -> 5 -> 6 -> 7 -> 8 -> 9 -> 10 -> 11 -> 12 -> 13 -> 14 -> 15 -> 16

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Sleeper Ingestion | 6/6 | Complete | 2026-03-22 |
| 2. Team Intelligence | 5/5 | Complete | 2026-03-22 |
| 3. Core Dashboard | 3/3 | Complete | 2026-03-22 |
| 4. Manager Profiling | 4/4 | Complete | 2026-03-22 |
| 5. Trade Intelligence | 4/4 | Complete | 2026-03-22 |
| 6. Dynamic Pick Valuation | 4/4 | Complete | 2026-03-22 |
| 7. Rookie Board & Draft Room | 4/4 | Complete | 2026-03-22 |
| 8. Historical Prospect Lab | 0/5 | Planned | - |
| 9. Portfolio & Retrospectives | 0/5 | Planned | - |
| 10. Pick Accuracy & Draft Order | 0/4 | Planned | - |
| 11. Roster & Lineup Intelligence | 4/5 | Gap Closure | 2026-03-25 |
| 12. Manager Rookie & Pick Profiles | 0/5 | Planned | - |
| 13. Context Awareness | 0/0 | Unplanned | - |
| 14. Trust Infrastructure | 0/0 | Unplanned | - |
| 15. Waiver & Startup Workflows | 0/0 | Unplanned | - |
| 16. Portfolio Thesis Expansion | 0/0 | Unplanned | - |
