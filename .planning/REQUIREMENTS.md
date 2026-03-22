# Requirements: Dynasty Fantasy Football Front Office OS

**Defined:** 2026-03-11
**Core Value:** Tell me what my team is, what my best path is, who to trade with, what kind of deal to make, and whether the prospect or pick decision I'm considering is actually sharp in this format and league.

## v1 Requirements

### Data Ingestion

- [x] **INGEST-01**: User can connect a Sleeper league by league ID and ingest all format settings (scoring system, roster positions, lineup slots, superflex/TEP/premium flags, bench/IR/taxi size)
- [x] **INGEST-02**: System ingests current rosters for all teams in a connected league including bench, IR, and taxi squad players
- [x] **INGEST-03**: System ingests current standings, points for, points against, and win/loss records per team
- [x] **INGEST-04**: System ingests all future rookie picks by team, year, and round (original owner and current holder)
- [x] **INGEST-05**: System ingests full trade history for the league including all assets exchanged, timestamps, and trade participants
- [x] **INGEST-06**: System ingests transaction history (adds, drops, waivers) for all managers
- [x] **INGEST-07**: User can manually correct any ingested data point (player position, pick value, roster assignment, league setting)
- [x] **INGEST-08**: System displays data freshness status and ingestion health per league with explicit gaps surfaced

### Team Intelligence

- [x] **TEAM-01**: System generates a team scorecard with 9 decomposed sub-scores: win-now, future value, depth, pick capital, flexibility, fragility, age risk, liquidity, and positional insulation
- [x] **TEAM-02**: System detects and recommends a primary team direction from 8 options: true contender, fragile contender, fringe playoff, productive struggle, one-year punt, retool, elite value accumulation, hard rebuild
- [x] **TEAM-03**: System provides confidence score, reasoning, and 2+ alternate viable directions for every direction recommendation; includes what would materially alter the label
- [x] **TEAM-04**: System surfaces direction implications: which valuation weights change, which move types are approved, which are discouraged
- [x] **TEAM-05**: System generates ranked move recommendations per team: top move types to execute and types to avoid given current direction and roster

### Dashboard

- [x] **DASH-01**: User sees a dashboard with a card per connected league showing direction label, confidence, and primary team weakness
- [x] **DASH-02**: Dashboard displays biggest value risers and fallers on the user's rosters across all leagues
- [ ] **DASH-03**: Dashboard alerts to cross-league exposure: players owned across 2+ leagues with concentration risk flags
- [x] **DASH-04**: Dashboard shows exploit windows: leaguemates currently showing behavioral triggers (losing trades, thin at a position, recent panic moves)

### Player Valuation

- [x] **PLAY-01**: System generates player values with 12 decomposed component scores: current production, short-term utility, role stability, age curve/decline risk, insulation value, market liquidity, positional scarcity, fragility/injury risk, ceiling, floor stability, rerollability, contract security proxy
- [x] **PLAY-02**: System reweights player values by league-specific format (scoring system, lineup requirements, positional scarcity in this league)
- [x] **PLAY-03**: System reweights player values by team direction (same player has materially different value on a rebuild vs. contending team)
- [x] **PLAY-04**: User can view a player across 5 simultaneous value lenses: production, market, insulation, team-fit, and direction-specific

### Trade Engine

- [x] **TRADE-01**: System evaluates any proposed trade on 7 dimensions: market fairness, roster fit, direction fit, timing quality, insulation gain/loss, liquidity gain/loss, and manager exploit quality — with confidence level per dimension
- [x] **TRADE-02**: System surfaces reroute paths: better targets for the same asset, 2-for-1/3-for-2 alternatives, pick-based versions of the move, tier-down options for insulation
- [x] **TRADE-03**: System generates package builder: fair range, best version of the trade, and manager-specific opening offer structures
- [x] **TRADE-04**: System distinguishes a market-fair but strategically mediocre trade from one that advances team direction

### Manager Profiling

- [x] **MGR-01**: System generates a dossier per leaguemate: roster summary, likely direction, positional needs, trade history trends, preferred asset types, and least-valued asset types
- [x] **MGR-02**: System assigns an exploitability score per manager with evidence count and confidence level; suppresses or labels LOW confidence below a defined minimum trade threshold
- [x] **MGR-03**: System surfaces recommended pitch angles per manager: opening offers, deal archetypes likely to be accepted, and offer structures to avoid
- [x] **MGR-04**: System distinguishes exploitation type: value-loss trader vs. timing-error trader vs. directionally-incoherent trader vs. archetype-specific overpayer

### Pick & Rookie Engine

- [x] **PICK-01**: System computes dynamic pick values adjusted for current standings, calendar timing (draft proximity), class strength perception, and active rebuilder count in this league
- [x] **PICK-02**: System adjusts pick values based on manager-specific demand signals within the league
- [x] **PICK-03**: System generates pick timing recommendations per pick: sell now / hold until rookie fever / use on the clock, with reasoning
- [x] **PICK-04**: System generates a format-aware rookie board with tiers, archetype labels, and risk bands for the current draft class
- [x] **PICK-05**: User can highlight players likely available at a given pick slot on the rookie board via slot availability filtering based on league draft tendencies (roster-fit reranking replaced by slot availability filtering per D-05/D-06)
- [x] **PICK-06**: Draft room view answers: best in abstract, best relative to this league's draft tendencies, and when trading the pick is superior (3 questions; "best for this roster" descoped per D-07)

### Prospect Lab

- [ ] **PROS-01**: System maintains a historical prospect database covering 10+ years with positional splits (QB, RB, WR, TE)
- [ ] **PROS-02**: System computes position-specific feature models using: age, athletic testing, production totals, market share, efficiency, usage profile, competition level proxy, and draft capital — with weights derived from backtesting, not hardcoded assumptions
- [ ] **PROS-03**: System produces threshold analysis, hit-rate buckets by draft capital tier, and archetype clustering from historical data
- [ ] **PROS-04**: System generates historical comps per prospect with hit-rate bucket assignment, risk band, and archetype label
- [ ] **PROS-05**: System identifies why a prospect may be overvalued or undervalued by the current market relative to historical positional evidence

### Portfolio & Memory

- [x] **PORT-01**: System saves league snapshots at scheduled and user-triggered intervals, capturing complete team state for future comparison
- [ ] **PORT-02**: User can compare current team state to any historical snapshot (scorecard, direction label, player values, pick capital)
- [ ] **PORT-03**: System tracks player ownership across all connected leagues and flags concentration exposure (owned in 3+ leagues, correlated injury risk)
- [ ] **PORT-04**: System surfaces portfolio-level risk: where the user is over-dependent on one player cluster, one team's success, or one directional thesis
- [ ] **PORT-05**: System grades past direction labels against actual outcomes after a season to surface calibration quality
- [ ] **PORT-06**: System grades past prospect tier assignments against historical outcomes to surface model accuracy

## v2 Requirements

### Data Ingestion

- **INGEST-V2-01**: System ingests previous rookie draft history (pick slot, player taken, trade-up/down history) if available on Sleeper

### Team Intelligence

- **TEAM-V2-01**: User can manually override the auto-detected team direction, and the system re-runs all downstream recommendations against the override

### Dashboard

- **DASH-V2-01**: Dashboard shows top 3 action items per team as explicit quick-links (best immediate trade target, sell-high, undervalued pick)

### Trade Engine

- **TRADE-V2-01**: System generates manager-specific pitch notes for any trade opportunity, tailored to the target manager's behavioral profile and known blind spots

## Out of Scope

| Feature | Reason |
|---------|--------|
| Automated trade offer submission | Sleeper API is read-only for trade execution; personal tool relies on manual action |
| Public-facing rankings or content | Personal intelligence tool — publishing destroys the league-specific edge |
| ESPN / Yahoo / MFL integration in v1 | Adapter pattern enables additions later; Sleeper first to validate core engines |
| Full custom model weight authoring | System stays opinionated in v1; manual corrections and notes supported everywhere |
| Weekly start/sit optimizer | Dynasty-focused product; redraft lineup optimization is commoditized elsewhere |
| Perfect player outcome prediction | Probabilistic confidence bands and sub-scores, never oracle-style single outputs |
| Film study replacement | Data and statistical signals only; film remains the user's independent judgment layer |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INGEST-01 | Phase 1 | Complete |
| INGEST-02 | Phase 1 | Complete |
| INGEST-03 | Phase 1 | Complete |
| INGEST-04 | Phase 1 | Complete |
| INGEST-05 | Phase 1 | Complete |
| INGEST-06 | Phase 1 | Complete |
| INGEST-07 | Phase 1 | Complete |
| INGEST-08 | Phase 1 | Complete |
| TEAM-01 | Phase 2 | Complete |
| TEAM-02 | Phase 2 | Complete |
| TEAM-03 | Phase 2 | Complete |
| TEAM-04 | Phase 2 | Complete |
| TEAM-05 | Phase 2 | Complete |
| DASH-01 | Phase 3 | Complete |
| DASH-02 | Phase 3 | Complete |
| DASH-03 | Phase 3 | Not Implemented — deferred to Phase 9 (PORT-03) |
| DASH-04 | Phase 3 | Complete |
| PLAY-01 | Phase 2 | Complete |
| PLAY-02 | Phase 2 | Complete |
| PLAY-03 | Phase 2 | Complete |
| PLAY-04 | Phase 2 | Complete |
| TRADE-01 | Phase 5 | Complete |
| TRADE-02 | Phase 5 | Complete |
| TRADE-03 | Phase 5 | Complete |
| TRADE-04 | Phase 5 | Complete |
| MGR-01 | Phase 4 | Complete |
| MGR-02 | Phase 4 | Complete |
| MGR-03 | Phase 4 | Complete |
| MGR-04 | Phase 4 | Complete |
| PICK-01 | Phase 6 | Complete |
| PICK-02 | Phase 6 | Complete |
| PICK-03 | Phase 6 | Complete |
| PICK-04 | Phase 7 | Complete |
| PICK-05 | Phase 7 | Complete — scope changed to slot availability filtering (D-05/D-06) |
| PICK-06 | Phase 7 | Complete — 3 questions (D-07 removed "best for this roster") |
| PROS-01 | Phase 8 | Pending |
| PROS-02 | Phase 8 | Pending |
| PROS-03 | Phase 8 | Pending |
| PROS-04 | Phase 8 | Pending |
| PROS-05 | Phase 8 | Pending |
| PORT-01 | Phase 3 | Complete |
| PORT-02 | Phase 9 | Pending |
| PORT-03 | Phase 9 | Pending |
| PORT-04 | Phase 9 | Pending |
| PORT-05 | Phase 9 | Pending |
| PORT-06 | Phase 9 | Pending |

**Coverage:**
- v1 requirements: 46 total
- Mapped to phases: 46
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-11*
*Last updated: 2026-03-22 — statuses updated after Phases 1–7 completion; DASH-03 noted as not implemented; PICK-05/PICK-06 scope changes documented*
