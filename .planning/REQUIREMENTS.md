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

### Format-Specific Intelligence

- [x] **FS-01**: System computes pick values and projected draft slots using each league's actual draft-order rules, not a universal inverse-standings assumption (Phase 10)
- [x] **FS-02**: System distinguishes a strong roster in abstract from a lineup that can actually win in the current format through an optimal lineup calculator, title-window label, and lineup-level direction signal (Phase 11)
- [x] **FS-04**: System surfaces actionable low-level roster moves below the trade layer including stash, cut, move-to-taxi, and consolidation suggestions per team, with taxi/IR occupancy and manual exceptions modeled per league (Phase 11)

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

## v1.1 Requirements — Helpfulness Overhaul

### Recommendation Contract

- [ ] **REC-01**: Every major module emits a structured recommendation card with at minimum: `recommendation_type`, `priority_rank`, `headline`, `action`, `target_entity_type`, `target_entity_ids`, `why_summary`, `supporting_factors[]`, `confidence_label`, `confidence_score`, `downside_of_inaction`, `what_would_change_this_call`, `horizon`, `league_specificity_notes`, `manager_specificity_notes`, `model_vs_market_gap`, `cta_label`, `cta_destination`
- [ ] **REC-02**: Each supporting factor includes: `factor_name`, `direction` (positive/negative/neutral), `magnitude`, `explanation`
- [ ] **REC-03**: Confidence contract is enforced: show confidence label + short uncertainty reason + what would change the call; never suppress moderate-confidence recommendations; never present false precision
- [ ] **REC-04**: Recommendation priority is computed via formula: `priority = impact × confidence × execution × urgency` where impact = title equity / EV effect, confidence = model trust, execution = realistic pullability, urgency = downside of waiting
- [ ] **REC-05**: Anti-overreaction layer applies stabilizing priors for: elite players with strong insulation, productive veterans with stable roles, players with explainable one-year dips, and players affected by temporary environmental changes
- [ ] **REC-06**: Player context flags are tracked and surfaced: QB upgrade/downgrade, coaching/play-caller change, depth-chart competition, injury recovery, age cliff proximity, likely role compression/expansion

### Market Inefficiency Layer

- [ ] **MKT-01**: Every asset carries parallel values: current-season lineup value, next-season dynasty value, market value, league-specific value, team-direction value, manager-demand value
- [ ] **MKT-02**: System computes a model-vs-market gap per asset: market rank/value, model rank/value, gap magnitude, direction of gap, explanation
- [ ] **MKT-03**: Each gap is classified as: buy low, sell high, hold despite weak market, ignore false discount, market right / model cautious, or league-specific opportunity
- [ ] **MKT-04**: Market gap layer is visible in player cards, trade recommendations, lineup recommendations, and stash/hygiene recommendations
- [ ] **MKT-05**: "Hold despite weak market" is a valid actionable conclusion the system can surface, not just buy/sell signals

### Competitive Outlook 2.0

- [ ] **COMP-01**: System replaces the 3-state title window (Inside/Fringe/Outside) with a minimum of 10 primary competitive states: Tier 1 Contender, Fragile Contender, Matchup-Dependent Contender, Playoff Team Not Yet a Favorite, Productive but Capped, Transitional Ascender, Delayed Window Builder, Asset-Rich Repositioner, Declining Contender, Hard Reset
- [ ] **COMP-02**: Each competitive state carries 1–3 secondary tags drawn from: Aging Core, Fragile at RB, Overexposed to One QB, Pick Poor, Deep but Star-Light, Star Heavy / Fragile Depth, Market Undervalued, Liquid Build, Overperforming Last Year, Dependent on Bouncebacks
- [ ] **COMP-03**: Every competitive outlook includes a recommended path (not just a label), current-year title odds band, next-year outlook, fragility score, and aging curve risk
- [ ] **COMP-04**: System emits dependency flags indicating which assets or results the competitive state is most contingent on

### Team Direction 2.0

- [ ] **DIR2-01**: Team direction output includes: primary label, 1–3 secondary tags, confidence score, key evidence, and recommended path
- [ ] **DIR2-02**: System explicitly detects "fake contender" cases: teams with contender label but insufficient elite starters or fragile ceiling
- [ ] **DIR2-03**: System explicitly detects "good team, bad bet" cases: teams with strong roster but poor expected value due to competition, aging risk, or ceiling cap
- [ ] **DIR2-04**: System explicitly detects "bad current team, good direction" cases: rebuilds with clear asset quality and plausible path to contention
- [ ] **DIR2-05**: Fewer than 25% of teams in a league should land in the same undifferentiated middle-tier bucket (e.g., productive struggle) without useful secondary differentiation
- [ ] **DIR2-06**: Primary direction label drives downstream trade suggestion logic, stash logic, and hygiene action priorities

### Lineup Strength 2.0

- [x] **LS-01**: Lineup scoring benchmarks against both league median and playoff/contender-team median — weakness means different things at each level
- [x] **LS-02**: Lineup benchmarks use median as default, not average, to reduce bias from outlier rosters
- [x] **LS-03**: Anti-overreaction guard: an elite-tier player (insulation score in top tier) cannot be labeled below replacement from raw recent production alone without contextual flags
- [x] **LS-04**: Every team receives at least one "best upgrade leverage point" recommendation with an estimated title equity improvement
- [x] **LS-05**: Lineup output separates "weak by median points" from "weak relative to contender path" — these are distinct signals
- [x] **LS-06**: Format premium adjustments apply: TE premium reduces urgency of TE weakness relative to equivalent RB weakness in standard formats

### Roster Hygiene 2.0

- [x] **HYG-01**: Hygiene engine emits 8 distinct action buckets: cut, hold, shop, package, taxi, handcuff/speculative hold, re-roll into pick, use as throw-in now
- [x] **HYG-02**: Every hygiene action includes timing logic: why now vs. hold for later, what triggers an action change
- [x] **HYG-03**: Packaging logic is explicit: "this player is more useful as a 2-for-1 sweetener than a standalone sell" is a valid and surfaced recommendation
- [x] **HYG-04**: Productive veterans with near-zero trade market are never lazily classified as sells — must show a willing buyer archetype or be classified as "hold despite weak market"
- [x] **HYG-05**: Every roster receives at least one determination each of: dead roster spot, liquid shop piece, and package candidate — where evidence supports it

### Trade Copilot 2.0

- [ ] **TRADE2-01**: Trade recommendations support 4 ranking modes: best blended EV, best chance of acceptance, best roster fit, best market win — user can select default
- [ ] **TRADE2-02**: Default trade ranking blends: roster improvement, direction fit, title equity impact, long-term value impact, acceptance probability, manager exploitability, timing
- [ ] **TRADE2-03**: Acceptance likelihood model uses manager behavioral history: if a manager repeatedly accepts negative-delta trades, the tool can recommend offers in that band
- [ ] **TRADE2-04**: Every trade recommendation includes: why this deal, why this manager, why now, estimated acceptance band, and open/fair/close/reroute options
- [ ] **TRADE2-05**: Every trade recommendation includes a "what to do if rejected" path
- [ ] **TRADE2-06**: If a manager hates a particular asset archetype (aging vets, injured players), the system stops surfacing that archetype to them unless new evidence overrides it

### Manager Dossier 2.0

- [ ] **MGR2-01**: Manager dossier adds derived behavioral fields: likely motivations right now, recent urgency state, time-of-calendar sensitivity, veteran appetite score, rookie fever index, value rigidity, reroute susceptibility
- [ ] **MGR2-02**: "Best asset to target" and "best asset to send" are separate explicit outputs, not combined into a single pitch
- [ ] **MGR2-03**: Dossier framing shifts from profile to exploit map: top section answers "how do I trade with this manager" with specific asset recommendations
- [ ] **MGR2-04**: Low-confidence badge remains enforced when behavioral evidence is thin (fewer than the defined minimum trade threshold)

### UX Recommendation Layer

- [ ] **UX-01**: Every major screen leads with a primary recommendation, then supporting metrics, then confidence, then downside of inaction, then what changes the call — in that hierarchy
- [ ] **UX-02**: League homepage top block surfaces a team memo: team state, competitive outlook, top 3 next actions, biggest risk, best trade partner, best leverage point
- [ ] **UX-03**: Lineup screen top section surfaces: strongest unit, weakest unit, title blocker, best leverage upgrade — before the detailed slot grid
- [ ] **UX-04**: Trade screen top section surfaces: best trade to send now, best manager to work with, best player archetype to target, reroute if target unavailable
- [ ] **UX-05**: Manager dossier top section answers: how to trade with this manager, what they are likely to buy, what they are likely to overpay for, what not to send first

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
| FS-01 | Phase 10 | Complete |
| FS-02 | Phase 11 | Complete |
| FS-04 | Phase 11 | Complete |
| REC-01 | Phase 17 | Pending |
| REC-02 | Phase 17 | Pending |
| REC-03 | Phase 17 | Pending |
| REC-04 | Phase 17 | Pending |
| REC-05 | Phase 17 | Pending |
| REC-06 | Phase 11 / Phase 17 | Partial - lineup/hygiene context flags complete |
| MKT-01 | Phase 17 | Pending |
| MKT-02 | Phase 17 | Pending |
| MKT-03 | Phase 17 | Pending |
| MKT-04 | Phase 17 | Pending |
| MKT-05 | Phase 17 | Pending |
| COMP-01 | Phase 18 | Pending |
| COMP-02 | Phase 18 | Pending |
| COMP-03 | Phase 18 | Pending |
| COMP-04 | Phase 18 | Pending |
| DIR2-01 | Phase 18 | Pending |
| DIR2-02 | Phase 18 | Pending |
| DIR2-03 | Phase 18 | Pending |
| DIR2-04 | Phase 18 | Pending |
| DIR2-05 | Phase 18 | Pending |
| DIR2-06 | Phase 18 | Pending |
| LS-01 | Phase 11 | Complete |
| LS-02 | Phase 11 | Complete |
| LS-03 | Phase 11 | Complete |
| LS-04 | Phase 11 | Complete |
| LS-05 | Phase 11 | Complete |
| LS-06 | Phase 11 | Complete |
| HYG-01 | Phase 11 | Complete |
| HYG-02 | Phase 11 | Complete |
| HYG-03 | Phase 11 | Complete |
| HYG-04 | Phase 11 | Complete |
| HYG-05 | Phase 11 | Complete |
| TRADE2-01 | Phase 19 | Pending |
| TRADE2-02 | Phase 19 | Pending |
| TRADE2-03 | Phase 19 | Pending |
| TRADE2-04 | Phase 19 | Pending |
| TRADE2-05 | Phase 19 | Pending |
| TRADE2-06 | Phase 19 | Pending |
| MGR2-01 | Phase 12 | Pending |
| MGR2-02 | Phase 12 | Pending |
| MGR2-03 | Phase 12 | Pending |
| MGR2-04 | Phase 12 | Pending |
| UX-01 | Phase 20 | Pending |
| UX-02 | Phase 20 | Pending |
| UX-03 | Phase 20 | Pending |
| UX-04 | Phase 20 | Pending |
| UX-05 | Phase 20 | Pending |

**Coverage:**
- v1 requirements: 49 total, mapped: 49 ✓
- v1.1 requirements: 47 total, mapped: 47 ✓
- Grand total: 96 requirements

---
*Requirements defined: 2026-03-11*
*Last updated: 2026-03-29 — Format-Specific Intelligence requirements formalized (FS-01, FS-02, FS-04); Phase 11 taxi manual exceptions gap closure executed; v1.1 Helpfulness Overhaul requirements retained*
