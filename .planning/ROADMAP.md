# Roadmap: Dynasty Fantasy Football Front Office OS

## Overview

This project builds a personal dynasty intelligence system in nine focused phases. Phases 1–3 deliver the core ingestion pipeline, team intelligence engines, and dashboard — the system's foundational thesis. A hard gate between Phase 3 and Phase 4 requires manual direction label validation against all active leagues before trade and manager intelligence is built on top of it. Phases 4–5 add counterparty intelligence and trade evaluation. Phases 6–7 deliver the dynamic pick engine and rookie tooling. Phase 8 builds the historical prospect lab with backtested models. Phase 9 closes the trust loop with portfolio-level exposure tracking and recommendation retrospectives.

## Phases

**Phase Numbering:**
- Integer phases (1–9): Planned milestone work
- Decimal phases (e.g., 3.1): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Sleeper Ingestion** - Stack scaffold, Sleeper adapter, full data ingest pipeline with health checks
- [ ] **Phase 2: Team Intelligence** - Team scorecard, direction detection, player valuation engines
- [ ] **Phase 3: Core Dashboard** - League card UI, dashboard views, snapshot table wire-in
- [ ] **Phase 4: Manager Profiling** - Leaguemate dossiers, exploitability scoring, pitch angle generation
- [ ] **Phase 5: Trade Intelligence** - Trade evaluator, reroute pathing, package builder
- [ ] **Phase 6: Dynamic Pick Valuation** - Standings-aware pick engine, demand signals, timing recommendations
- [ ] **Phase 7: Rookie Board & Draft Room** - Format-aware rookie tiers, roster-fit overlays, draft room view
- [ ] **Phase 8: Historical Prospect Lab** - 10+ year database, backtested position models, archetype clustering
- [ ] **Phase 9: Portfolio & Retrospectives** - Cross-league exposure, season-over-season snapshots, retrospective grading

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
  5. The ingest pipeline runs against incomplete or partial Sleeper API responses without crashing — null gaps are surfaced, not silently dropped
**Plans**: 6 plans

**Open question resolved:** Scoring history uses nfl_data_py (not Sleeper's deprecated player stats endpoint). Fantasy points reconstructed from raw stat lines using each league's actual scoring_settings. 10+ years of data ingested in Phase 1 to seed Phase 8's Historical Prospect Lab.

**Open question resolved:** Global Asset Baseline seeded from two sources: ADP signals (FantasyPros dynasty ADP CSV) + nfl_data_py scoring reconstruction. Baseline is foundation-only in Phase 1; Phase 2 applies league-specific adjustments on top.

Plans:
- [ ] 01-00-PLAN.md — Project scaffold: FastAPI skeleton, DuckDB schema + Alembic migrations, test stubs
- [ ] 01-01-PLAN.md — SleeperMapper adapter: domain models (LeagueSettings, RosterSnapshot, TradedPick, StandingRow, TransactionRecord)
- [ ] 01-02-PLAN.md — Repository layer: LeagueRepo DuckDB upserts + NflDataPyLoader with fantasy point reconstruction
- [ ] 01-03-PLAN.md — SleeperClient (httpx + tenacity) + IngestService orchestration with all-weeks transaction loop
- [ ] 01-04-PLAN.md — OverrideService (corrections CRUD) + FastAPI routers (ingest, corrections) wired into main.py
- [ ] 01-05-PLAN.md — GapDetector + health endpoint + ADP baseline loader + human-verify checkpoint

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
**Plans**: TBD

Plans:
- [ ] 02-01: TBD
- [ ] 02-02: TBD

---

### Phase 3: Core Dashboard
**Goal**: The dashboard surfaces direction labels, value changes, cross-league exposure, and exploit windows per connected league — and the snapshot table is wired in so early data is never lost
**Depends on**: Phase 2
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, PORT-01
**Success Criteria** (what must be TRUE):
  1. User sees a card per connected league on load showing direction label, confidence level, and primary team weakness — visible without scrolling or expanding sub-panels
  2. Dashboard displays biggest value risers and fallers across all connected leagues
  3. Dashboard alerts fire for players owned across 2+ leagues with concentration risk flags
  4. Dashboard surfaces leaguemates currently showing behavioral triggers (losing trades, positional thinness, recent panic moves)
  5. League snapshots are saved automatically at scheduled intervals and on user trigger — early snapshots cannot be recovered retroactively, so this must be live before Phase 4
**Plans**: 3 plans

**HARD GATE — Phase 3 exit:** Before Phase 4 begins, direction labels must be manually reviewed and confirmed against all active leagues. If a direction label is materially wrong (e.g., a clear rebuild labeled as a contender), Phase 4 and Phase 5 must not proceed until the engine is corrected. This gate is not optional.

Plans:
- [ ] 03-01-PLAN.md — Backend: snapshot migration, SnapshotService, dashboard + snapshot routers, post-ingest hook
- [ ] 03-02-PLAN.md — Frontend scaffold: Vite + React 19 + TanStack Router/Query + shadcn/ui init + route shells + API queries
- [ ] 03-03-PLAN.md — Frontend views: LeagueCard grid, drill-in with risers/fallers + exploit windows + snapshot controls + human-verify

---

### Phase 4: Manager Profiling
**Goal**: The system generates a dossier per leaguemate with evidence-backed exploitability scoring, suppressing or labeling LOW confidence where trade evidence is insufficient
**Depends on**: Phase 3 (direction gate cleared)
**Requirements**: MGR-01, MGR-02, MGR-03, MGR-04
**Success Criteria** (what must be TRUE):
  1. User can view a dossier per leaguemate showing roster summary, likely direction, positional needs, trade history trends, preferred asset types, and least-valued asset types
  2. Exploitability score is displayed with evidence count prominently; any dossier with fewer than 10 trades in evidence shows a LOW confidence label — the threshold is a named constant, not a magic number
  3. Recommended pitch angles per manager are surfaced with deal archetypes likely to be accepted and structures to avoid
  4. Each dossier distinguishes exploitation type: value-loss trader, timing-error trader, directionally-incoherent trader, or archetype-specific overpayer
**Plans**: 4 plans

Plans:
- [ ] 04-01-PLAN.md — Backend foundation: profiling constants, Pydantic models, Alembic migration 006, ProfilingRepo
- [ ] 04-02-PLAN.md — Backend engine + router: ProfilingEngine (exploitation classification, scoring, pitch angles), FastAPI router, unit tests
- [ ] 04-03-PLAN.md — Frontend managers list: shadcn install (tabs/table/alert), ManagerListRow, managers route, Phase 3 ExploitWindowPanel link update
- [ ] 04-04-PLAN.md — Frontend dossier: DossierPage with tabs, Overview/TradeHistory/PitchAngles tab components, human-verify checkpoint

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
**Plans**: TBD

Plans:
- [ ] 05-01: TBD
- [ ] 05-02: TBD

---

### Phase 6: Dynamic Pick Valuation
**Goal**: Pick values are computed dynamically from current standings, draft proximity, class strength, and league-specific rebuilder count — with timing recommendations per pick
**Depends on**: Phase 5
**Requirements**: PICK-01, PICK-02, PICK-03
**Success Criteria** (what must be TRUE):
  1. Pick values update when standings change — a team going on a losing streak changes that pick's value at evaluation time, not at a fixed schedule
  2. Pick values reflect manager-specific demand signals within the league (a known rebuilder wanting early picks is priced in)
  3. Each pick shows a timing recommendation (sell now / hold until rookie fever / use on the clock) with reasoning tied to current standing trajectory and class strength perception
**Plans**: TBD

**Research flag:** Phase 6 planning should use `/gsd:research-phase` before implementation. The dynamic pick valuation algorithm (class strength weighting, rebuilder count adjustment, calendar timing decay) has dynasty community methodology nuances worth researching before specifying the formula.

Plans:
- [ ] 06-01: TBD
- [ ] 06-02: TBD

---

### Phase 7: Rookie Board & Draft Room
**Goal**: The system produces a format-aware rookie board with tiered rankings and roster-fit overlays, and the draft room view answers the four key questions a manager needs on the clock
**Depends on**: Phase 6
**Requirements**: PICK-04, PICK-05, PICK-06
**Success Criteria** (what must be TRUE):
  1. Rookie board displays tiers, archetype labels, and risk bands adjusted for the active league's scoring format and lineup requirements
  2. User can filter the rookie board to show roster-fit rankings for a specific team — who is best for this team vs. best in the abstract are clearly distinguished
  3. Draft room view answers: best in abstract, best for this roster, best relative to this league's draft tendencies, and when trading the pick is the superior play
**Plans**: TBD

Plans:
- [ ] 07-01: TBD
- [ ] 07-02: TBD

---

### Phase 8: Historical Prospect Lab
**Goal**: The system maintains a backtested historical prospect database and generates evidence-backed tier assignments, archetype clustering, and historical comps per prospect
**Depends on**: Phase 7
**Requirements**: PROS-01, PROS-02, PROS-03, PROS-04, PROS-05
**Success Criteria** (what must be TRUE):
  1. Historical prospect database covers 10+ years with positional splits; user can query it from the UI
  2. Position-specific feature models exist for QB, RB, WR, and TE with weights derived from backtested hit rates, not hardcoded assumptions
  3. Each current prospect shows: tier, archetype label, historical comps, hit-rate bucket, and risk band
  4. System flags why a prospect is overvalued or undervalued by the current market relative to historical positional evidence — the flag includes the specific divergence
**Plans**: TBD

**Research flag:** Phase 8 planning requires `/gsd:research-phase` before implementation. ML model selection with small prospect sample sizes is non-trivial; the NFLverse ETL pipeline needs API investigation; time-based train/test split methodology needs verification before any model is specified.

Plans:
- [ ] 08-01: TBD
- [ ] 08-02: TBD

---

### Phase 9: Portfolio & Retrospectives
**Goal**: The system tracks cross-league player exposure and portfolio-level risk, enables season-over-season comparison against historical snapshots, and grades past direction labels and prospect tiers against actual outcomes
**Depends on**: Phase 8
**Requirements**: PORT-02, PORT-03, PORT-04, PORT-05, PORT-06
**Success Criteria** (what must be TRUE):
  1. User can view player ownership across all connected leagues with concentration exposure flags (owned in 3+ leagues, correlated injury risk)
  2. User can compare any team's current state to a historical snapshot — scorecard, direction label, player values, and pick capital all comparable side by side
  3. System grades past direction labels against actual season outcomes and surfaces calibration quality (was "true contender" calibrated?)
  4. System grades past prospect tier assignments against NFL outcomes and surfaces model accuracy per position and tier
**Plans**: TBD

Plans:
- [ ] 09-01: TBD
- [ ] 09-02: TBD

---

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → [GATE] → 4 → 5 → 6 → 7 → 8 → 9

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Sleeper Ingestion | 0/6 | Planned | - |
| 2. Team Intelligence | 0/TBD | Not started | - |
| 3. Core Dashboard | 0/3 | Planned | - |
| 4. Manager Profiling | 0/4 | Planned | - |
| 5. Trade Intelligence | 0/TBD | Not started | - |
| 6. Dynamic Pick Valuation | 0/TBD | Not started | - |
| 7. Rookie Board & Draft Room | 0/TBD | Not started | - |
| 8. Historical Prospect Lab | 0/TBD | Not started | - |
| 9. Portfolio & Retrospectives | 0/TBD | Not started | - |
