# Pitfalls Research

**Domain:** Dynasty fantasy football intelligence system / personal sports analytics
**Researched:** 2026-03-11
**Confidence:** HIGH (domain-specific pitfalls verified across multiple sources; engineering pitfalls drawn from established patterns in sports analytics ML literature and Sleeper API documentation)

---

## Critical Pitfalls

### Pitfall 1: False Precision in Dynasty Valuation

**What goes wrong:**
The system produces a single numerical score or recommendation with enough apparent precision that the user treats it as ground truth. A player's "value" shown as 4,820 vs. 4,650 implies a meaningful difference that does not exist. Confidence intervals collapse into point estimates. Recommendations are stated without showing what assumptions they rest on or what would break them.

**Why it happens:**
Point estimates are easier to display and code than probability ranges. Developers default to "what's the number?" interfaces because they're straightforward to implement. The temptation is to resolve all the model's internal uncertainty into a clean output so the UI stays simple — but this buries the most important information the user needs to evaluate the recommendation.

**How to avoid:**
Every recommendation must carry a visible confidence band and a "what breaks this thesis" note from day one. Sub-scores (win-now, future value, fragility, pick capital) must be shown alongside the summary label — never hidden. Player values must be presented as ranges or tier buckets, not single integers. Trade evaluations must show the distribution of possible outcomes, not just the net value. The architecture must be designed so confidence propagates through the engine, not gets stripped at the output layer.

**Warning signs:**
- UI designs show a single ranked number without any range or confidence indicator
- Users (you) begin making decisions that treat model output as definitive rather than as one input
- Recommendations are given without reasoning text attached
- The model produces the same format of output regardless of how much data it has for a given player or manager

**Phase to address:**
Phase 1 (Core league ingest and team intelligence) — the scorecard format must bake in confidence levels and sub-scores before any recommendation engine is built on top of it. If the output format defaults to false precision in Phase 1, every later phase inherits the problem.

---

### Pitfall 2: Over-Reliance on Consensus Market Value (KTC / Community Pricing)

**What goes wrong:**
Market consensus values (from sources like KeepTradeCut) are crowdsourced from a large general population playing in generic scoring formats. They do not reflect your league's specific scoring, roster settings, or competitive ecosystem. Building the trade evaluator on top of a consensus baseline treats these as "true value" — which they are not. The system ends up telling you whether a trade is fair relative to what the average dynasty community thinks, not whether it's sharp relative to your specific situation.

**Why it happens:**
Consensus values are the most available, structured external signal. They're an easy shortcut for seeding the valuation layer. It feels like anchoring to reality rather than making everything up from scratch. The error is conflating "market price in a large population" with "value in this specific context."

**How to avoid:**
Consensus values must be treated as one input signal, not the baseline. The system's own league-specific adjusted values — derived from the actual scoring format, roster construction, and team direction context — must be the primary output. Consensus values can be stored as a reference point to surface when a player's context-adjusted value materially diverges from the market (which is itself a signal). KTC-style values should appear in the UI as a comparison, never as the anchor.

**Warning signs:**
- Trade fairness scoring is implemented as a percentage of KTC values exchanged
- The system has no mechanism to produce a value that contradicts consensus
- Format adjustments (TEP, superflex, premium scoring) are applied as simple percentage modifiers on top of consensus rather than as first-class inputs to valuation
- Recommendations describe trades as "fair value" without reference to team direction fit

**Phase to address:**
Phase 2 (Trade intelligence) — before the trade evaluator is built, the format-adjusted and direction-adjusted player values from Phase 1 must be confirmed as structurally independent from any external consensus baseline. Phase 2 can layer consensus as a comparison point, not as the foundation.

---

### Pitfall 3: Prospect Model Overfitting to Historical Patterns

**What goes wrong:**
The historical prospect database (Phase 4) contains a limited number of true "hits" per position per draft capital tier — perhaps 8-15 reliable data points for a given archetype over 10 years. Models trained on this data will fit the noise in the historical sample and appear highly accurate on backtesting while having poor predictive validity on new prospects. Feature selection becomes circular: the features that best predict past hits happen to describe the players who were already considered good prospects, embedding the market's prior into the model.

**Why it happens:**
Small sample sizes (NFL draft produces ~50 skill-position prospects per year, not all get real opportunity, and "hit" is hard to define consistently) make ML overfitting structurally likely. Historical NFL draft data is inherently noisy — scheme fit, injury, opportunity, and coaching quality all confound the signal from pre-draft indicators. Developers build models with all available features and optimize for training set performance, producing impressive-looking hit rates that don't generalize.

**How to avoid:**
Position-specific sample sizes must be documented before any model is built — if a TE archetype bucket has fewer than 30 examples, a full ML model is not appropriate. Use simpler, more interpretable methods (threshold analysis, bucket comparisons, historical comp matching by similarity score) that cannot silently overfit. Treat model outputs as "this prospect has attributes that historically correlate with outcomes like X" rather than "this prospect has a 74% chance of hitting." Backtest on held-out time windows (e.g., train on 2013-2020, validate on 2021-2024), not random splits. Document feature selection rationale — every feature included must have a non-circular causal argument for why it should predict NFL success.

**Warning signs:**
- Backtested hit rates look suspiciously high (above 65-70% for a binary hit/bust definition)
- The model ranks the same prospects the market has already priced as the top prospects
- Validation is done with random train/test splits rather than time-based splits
- Feature importance shows pre-draft capital (i.e., where the market already priced them) as the top predictor

**Phase to address:**
Phase 4 (Historical prospect lab) — this phase must begin with an explicit sample size audit per position before model selection. The roadmap for Phase 4 should build threshold analysis and comp matching before attempting any predictive model, using simpler tools as the validation baseline.

---

### Pitfall 4: Manager Behavior Inference from Insufficient Transaction History

**What goes wrong:**
A leaguemate's "dossier" is built from 3-8 completed trades across one or two seasons. The system produces a confident profile: "This manager overpays for elite WRs and is exploitable on picks." This profile is used to drive real trade targeting and pitch angle recommendations. But 4 trades is not enough to distinguish consistent behavior from situational noise — a manager who made two sell-high moves during a rebuild does not have an established pattern of selling veterans.

**Why it happens:**
The feature is conceptually compelling and relatively easy to code — aggregate trades, tag them with categories, produce ratios. The danger is invisible because the output looks authoritative even when it's based on 3 data points. Sleeper's API provides trade objects but only for the current or recent seasons, meaning historical transaction depth is structurally limited.

**How to avoid:**
Every manager profile must display its evidence count prominently — the number of trades the profile is based on. When count is below a meaningful threshold (e.g., fewer than 10 trades), confidence must be explicitly set to LOW and recommendations must be labeled "preliminary profile." The system must distinguish between "observed pattern" (enough trades to see consistency) and "observed behavior" (one or two events that could be anomalous). Profiles must reset or degrade when roster composition changes significantly (rebuilding managers trade differently than contenders). Manual notes must be first-class on every dossier.

**Warning signs:**
- Profile confidence scores do not decrease as trade count decreases
- The system makes specific pitch angle recommendations based on a manager with fewer than 5 observed trades
- Profiles do not distinguish between trades made in different team contexts (rebuild vs. contend)
- No mechanism exists to manually override or annotate a profile

**Phase to address:**
Phase 2 (Trade intelligence and manager dossiers) — the dossier architecture must encode sample size as a first-class attribute before any scoring or recommendation layer is built on top of it.

---

### Pitfall 5: Sleeper API Data Gaps Treated as Complete Data

**What goes wrong:**
The Sleeper API is used as the sole data source and its output is treated as authoritative. In practice, several critical data categories have structural gaps: the player stats endpoint has been deprecated from the open API, meaning historical scoring data must be reconstructed from league matchup records (lossy and league-specific, not player-universal). Full multi-year trade history is not always available. Player metadata fields are inconsistent and some may be missing or empty. The system is built assuming data completeness, and fails silently or produces misleading outputs when fields are missing.

**Why it happens:**
The Sleeper API is free, well-documented, and covers the core league data well. Developers assume the "nice" parts of the API (rosters, standings, picks) represent the full picture. The stats deprecation is a known issue in the dynasty developer community but not prominently surfaced in the official docs. Fields that are absent simply aren't returned, making it easy to miss their absence until the analysis produces an anomaly.

**How to avoid:**
Build an explicit data availability layer before any analysis engine runs. Every data domain (player stats, trade history, draft history, manager profiles) must have a completeness check that surfaces gaps to the user and records them in the system state. Analysis engines must handle missing fields gracefully — returning a null or a "data unavailable" state rather than computing on empty data. Player scoring history should be reconstructed from matchup records where possible, but the reconstruction's completeness must be tracked per player. Manual override must be available for every data domain to fill gaps.

**Warning signs:**
- Engines are coded assuming field presence (e.g., `player['stats']['rushing_yards']` without null checks)
- Player scoring history is used without tracking which seasons and weeks have complete data
- Trade history analysis silently skips trades where pick data is malformed
- The system has no "data health" dashboard or per-domain completeness indicator

**Phase to address:**
Phase 1 (Core league ingest) — the ingest layer must be hardened for missing and inconsistent data before any analysis layer is built. Data health indicators must be first-class outputs of the ingest pipeline, not an afterthought.

---

### Pitfall 6: Building Too Many Engines Before Validating the Core

**What goes wrong:**
The system has six modular engines (global baseline, league context, team direction, manager behavior, trade pathing, prospect research). All six are scoped and partially built before the first engine — team direction detection — has been validated against real use. The team direction logic is the foundation every other engine rests on. If it produces labels that don't match the manager's actual read of the situation, every downstream recommendation is wrong. Six months of development produces a system that is comprehensive but wrong in ways that are hard to isolate.

**Why it happens:**
Building parallel systems is satisfying. It feels like making progress on all fronts. The interconnections between engines make it tempting to scaffold them simultaneously. The specific failure of "direction detection doesn't match my read of the team" is only discoverable by using the system on real data — which doesn't happen until late in development.

**How to avoid:**
Validate the direction engine on all active leagues before building Phase 2. The check is simple: does the direction label and reasoning match what the manager already knows about the team? If the system labels a clear rebuild as a "contender" or assigns wrong confidence, the scoring model is miscalibrated and must be fixed before the trade evaluator is built on top of it. Each engine should be validated in production use before the next engine is scaffolded. Build the retrospective layer (Phase 5) early — even a lightweight version — so you can check whether previous direction labels held.

**Warning signs:**
- Phase 2 is started before Phase 1 direction labels have been spot-checked against manual assessment
- No explicit "does this match your read?" validation step is included in Phase 1 acceptance criteria
- Trade evaluator output is being designed before team direction output has been reviewed
- The system has no mechanism to record "this direction label was wrong" for future calibration

**Phase to address:**
Phase 1 (Core league ingest) must include a validation gate: direction labels must be manually reviewed before Phase 2 scope begins. The PROJECT.md already states "ship to validate" — this must be enforced as a literal phase gate, not a principle.

---

### Pitfall 7: UI Complexity Creep Burying the Recommendations

**What goes wrong:**
The dashboard accumulates sub-scores, charts, tables, and indicators until the primary output — "here are your 3 action items" — is visually buried or requires scrolling to reach. The system becomes a data display tool rather than a decision support tool. Users (you) stop trusting the system's synthesis and instead manually read the sub-scores and form their own conclusions, defeating the purpose of the engine layer.

**Why it happens:**
Sub-scores are individually interesting. It's tempting to surface everything the system computed because each piece feels valuable. Dashboards grow incrementally — one panel at a time — with no forcing function to cut. The design defaults to "more information is better" rather than "right information, at the right level."

**How to avoid:**
Design the UI from the recommendation down, not from the data up. The top of every league view must show the direction label and the top 3 action items. Sub-scores must be collapsible or on a secondary view. Before adding any new UI panel, ask whether it changes what decision the user makes — if not, it belongs in a drill-down, not the primary view. Set a rule: the first visible screen of any league card must contain a decision recommendation, not raw data.

**Warning signs:**
- The homepage shows more than three primary information panels before showing a recommendation
- Sub-score tables are the first thing rendered on a league card
- The design review focuses on whether data is displayed correctly rather than whether the recommendation is surfaced clearly
- Adding new data fields is described as a feature rather than a cost

**Phase to address:**
Phase 1 (Dashboard) — the initial dashboard design must be validated on the "decision first" principle before any additional data panels are added. This is a Phase 1 UX constraint that must be stated explicitly in the design brief.

---

### Pitfall 8: Treating Pick Valuation as Static Within a Season

**What goes wrong:**
Draft pick values are computed once at the start of the season (or at ingest time) and treated as fixed for evaluation purposes. In reality, picks have significant dynamic pricing: early picks increase in value during the regular season as standings clarify, decrease after the draft when the class is revealed and priced, and shift dramatically when a rebuilding team's standings change. A 2026 first-round pick acquired in September when the league is uncertain is worth considerably more than the same pick evaluated after the season establishes it as a mid-round selection.

**Why it happens:**
Static pick values are easy to implement. The Sleeper API returns the traded picks object with round and owner, not a dynamic price. Developers assign a value (often from KTC) at ingest time and treat it as the pick's value until manually refreshed.

**How to avoid:**
Pick valuations must be parameterized by: draft year, current standings of the original owner, time of year (pre-draft, post-draft, in-season), and class strength signal. The engine must recompute pick values on each data refresh using current standings context, not store them as fixed values. The UI must show picks with their current conditional value ("this pick is currently projected as a 1.05 based on the original owner's record") rather than a generic round label.

**Warning signs:**
- Pick values stored in the database rather than recomputed at evaluation time
- Trade evaluations use round labels ("1st round pick") without reference to the original owner's current standings
- No class strength variable exists in the pick valuation formula
- Pick value is not recalculated when standings are refreshed

**Phase to address:**
Phase 3 (Dynamic pick engine) — this is the defining design challenge of that phase and must be the first thing specified before implementation begins.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcode player positions as static attributes | Faster ingest | Fails when players change positions mid-career (RB-to-WR, TE eligibility changes, QB to SF flex) — valuation engine breaks silently | Never — use Sleeper's position field with manual override support |
| Use KTC values as the primary player valuation baseline | Seeded values from day one | Consensus bias propagates into every recommendation; system can never surface a contrarian view | Never for primary valuation — acceptable as a secondary comparison signal |
| Skip data completeness checks and assume fields exist | Faster initial development | Silent failures when Sleeper returns incomplete or deprecated data; produces misleading outputs | Never — null handling must be in the ingest layer from the start |
| Build all six engines simultaneously before validating any | Feels like parallel progress | Direction model miscalibration cannot be detected until everything is built; wasted work across dependent engines | Never — sequential validation gates are required |
| Store sub-scores as a single opaque composite score | Simpler UI and storage | Impossible to explain why a recommendation changed; impossible to debug or tune individual dimensions | Never — sub-scores must be individually stored and surfaced |
| Use random train/test splits for prospect model validation | Easy to implement, produces high accuracy metrics | Overfitting to historical noise; hit rates don't generalize to new prospects | Never for time-series data — use time-based splits only |
| Infer manager tendencies from 2-3 trades | Profile generated immediately | Confidently wrong profiles drive bad trade targeting; damages trust in the system | Acceptable only if labeled explicitly as "preliminary" with sample count displayed |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Sleeper API — player stats | Querying the player stats endpoint expecting current scoring data | The endpoint is deprecated from Sleeper's open API. Reconstruct scoring history from league matchup records per season or use the weekly matchup data to accumulate stats locally |
| Sleeper API — player list | Fetching the full player list on every request | The endpoint returns ~5MB of data and is documented as "once per day at most." Cache locally and refresh daily; treat it as a static reference dataset |
| Sleeper API — trade history | Treating the trade object as containing complete pick data | Traded picks objects may have empty or inconsistent `previous_owner_id` fields. Validate and sanitize every pick object; track data quality per trade |
| Sleeper API — rate limits | Making burst requests during data refresh cycles | The API is undocumented on exact limits but documented as "stay under 1000 calls per minute." Implement request queuing with a conservative rate limiter in the ingest layer |
| Sleeper API — league settings | Assuming scoring settings are complete and consistent | Manual league settings (custom scoring rules, unusual roster configurations) may not be fully represented in the API response. Build a settings override layer that surfaces incomplete configs for manual correction |
| External player data (ADP, combine, college stats) | Coupling the analysis engine directly to an external data provider | External data sources change format, deprecate endpoints, or go offline. Use an abstraction layer with a normalized internal data model; external providers are adapters, not hard dependencies |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Recomputing all team direction scores on every page load | Dashboard becomes slow as league data grows; full re-evaluation runs on every navigation | Cache scored snapshots with a last-updated timestamp; only recompute when underlying data has changed since last snapshot | Immediately visible with 3 leagues × 12 teams each |
| Fetching full player list on every trade evaluation | Evaluation calls are slow; Sleeper API is hammered | Cache the player list locally, refresh daily maximum | Every trade evaluation call |
| Storing all historical trade/transaction data in memory during analysis | Memory spikes during full season ingests | Paginate through transaction history, process in chunks, persist to local DB rather than holding in memory | With multi-season history across 3 leagues |
| Running prospect model scoring on every roster view | Roster pages slow when many rostered prospects exist | Pre-score and cache prospect evaluations at ingest time; only re-score on manual refresh or when roster changes | With deep rosters (30+ rostered players) |
| Recalculating pick values on every render rather than on data refresh | Pick-heavy trade evaluations are slow | Compute pick values during the data refresh cycle and store computed values; re-trigger only when standings change | Immediately visible in the trade evaluator with multiple pick packages |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Showing all sub-scores on the primary league card | Cognitive overload; the recommendation is buried below data; the system feels like a spreadsheet, not an advisor | Surface direction label + top 3 actions on the primary card; all sub-scores available in a drill-down view |
| Expressing player values as single integers | Users anchor to specific numbers; minor model changes cause confusion about "why did the value change?"; false precision drives bad decisions | Use tier labels (Elite, Tier 1, Tier 2, etc.) as the primary display; numerical ranges shown only in drill-down |
| Showing recommendations without showing the reasoning | Users distrust outputs they can't explain; system feels like a black box | Every recommendation must have an inline "why" — the 2-3 driving factors that produced it |
| Displaying confidence as a percentage without context | "74% confidence" is meaningless without explaining what would change it | Show confidence as HIGH/MEDIUM/LOW with a "what could break this" note rather than a precise number |
| Treating all leagues identically in the portfolio view | Cross-league recommendations don't account for different team directions; a "sell DeVonta Smith" recommendation in one league conflicts with "hold" in another without explanation | Every recommendation must be scoped to its league context; the portfolio view surfaces conflicts explicitly, not silently merges them |
| Making the manual correction UX secondary or hidden | Users find overrides but don't trust they'll be respected; they stop correcting the system and stop trusting it | Manual corrections must be first-class, prominently placed, and visibly reflected in downstream outputs with a "manual override active" indicator |

---

## "Looks Done But Isn't" Checklist

- [ ] **Direction detection:** Shows a label and confidence score — verify it also shows the top 3 driving factors and what would change the direction recommendation
- [ ] **Trade evaluator:** Shows a value delta — verify it also accounts for team direction fit, timing, insulation, and manager exploit quality (not just raw value exchange)
- [ ] **Manager dossier:** Shows tendencies and an exploitability score — verify the evidence count is displayed prominently and the profile degrades to LOW confidence below threshold
- [ ] **Pick valuations:** Shows a pick value — verify it is being computed from current standings of the original owner, not stored as a static round value
- [ ] **Prospect scores:** Shows a tier and archetype — verify the sample size of the archetype bucket is documented and the model's training window is disclosed
- [ ] **Data ingest:** Shows "last refreshed" timestamp — verify a data health indicator shows completeness per domain (stats, trades, draft history), not just that the refresh ran
- [ ] **Portfolio view:** Shows cross-league exposure — verify it surfaces conflicting recommendations between leagues rather than silently aggregating them
- [ ] **Sub-scores:** Displayed in UI — verify they are individually persisted in storage and not recomputed from a single stored composite

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| False precision baked into early output format | HIGH | Requires redesigning the output schema to carry confidence ranges; all downstream engines that consume the output must be updated; significant refactor |
| KTC as primary valuation baseline | HIGH | Requires rebuilding the valuation layer with league-specific context as the primary signal; all existing trade recommendations and history become suspect |
| Prospect model overfit discovered post-build | MEDIUM | Rebuild with time-based splits and simpler models; discard overfit model outputs and re-score all prospects; re-validate hit rates |
| Manager profiles built on insufficient data with no confidence decay | LOW-MEDIUM | Add sample count field to profile schema, add confidence thresholding logic; update UI to surface evidence count; existing profiles can be recalculated |
| Sleeper API data gap failures discovered in production | MEDIUM | Add data completeness layer to ingest pipeline; audit all fields for null handling; add manual override UI for affected domains; some historical analyses may be irrecoverable |
| Direction engine miscalibrated, discovered after Phase 2 is built | HIGH | Must recalibrate direction scoring, rerun all trade recommendations that depended on direction fit, potentially invalidate existing phase 2 outputs |
| UI complexity creep makes dashboard unusable | MEDIUM | Requires UX audit and deliberate removal of panels; technical cost is low but requires discipline to cut features that were built |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| False precision in dynasty valuation | Phase 1 | All scorecard outputs carry confidence levels and sub-scores; no single integer values for player ratings |
| Over-reliance on consensus market value | Phase 1 (before Phase 2) | Format-adjusted values are computed before any external consensus value is ingested; KTC stored as comparison only |
| Prospect model overfitting | Phase 4 | Sample size audit documented before model selection; backtest uses time-based splits; hit rates on held-out window match expectations |
| Manager behavior inference from small samples | Phase 2 | All dossiers display evidence count; recommendations suppressed or labeled LOW confidence below 10-trade threshold |
| Sleeper API data gaps treated as complete | Phase 1 | Ingest pipeline produces a per-domain data health report; null handling tested with incomplete response fixtures |
| Building engines before validating core | Phase 1 → Phase 2 gate | Direction labels manually reviewed against all active leagues before Phase 2 scope is opened |
| UI complexity creep | Phase 1 (dashboard) | Primary league card shows direction + 3 actions before any sub-score panels; UX principle enforced as a design constraint |
| Static pick valuations | Phase 3 | Pick values recomputed from standings at evaluation time; no stored round-to-value mapping used as primary source |

---

## Sources

- [Sleeper API Official Docs](https://docs.sleeper.com/) — rate limits, deprecated stats endpoint, read-only scope, player list endpoint restrictions
- [ffscrapr — Sleeper player scores deprecation](https://ffscrapr.ffverse.com/) — confirms Sleeper deprecated their open API endpoint for player scores
- [KeepTradeCut FAQ](https://keeptradecut.com/frequently-asked-questions) — crowdsourced ELO algorithm, .5ppr default, limitations of consensus values
- [Dynasty Trade Calculator community analysis](https://forum.dynastyleaguefootball.com/viewtopic.php?t=245428) — league-specific limitations of trade calculators
- [Footballguys — Finding Truth in Leaguemate Tendencies (2024)](https://www.footballguys.com/article/2024-finding-truth-in-leaguemate-tendencies) — behavioral inference from limited trade observation
- [Footballguys — Hidden Yardage: Bias in Fantasy Football (2024)](https://www.footballguys.com/article/2024-hidden-yardage-exploring-the-bias-in-fantasy-football) — cognitive biases affecting manager decision-making
- [PFF — Historical hit rates by position (2025)](https://www.pff.com/news/draft-what-historical-hit-rates-reveal-about-positional-success) — positional scarcity and draft capital hit rates
- [Northwestern Sports Analytics — ML for NFL prospect success (2024)](https://sites.northwestern.edu/nusportsanalytics/2024/03/29/using-machine-learning-and-college-profiles-to-predict-nfl-success/) — overfitting risks in prospect models
- [Machine Learning for sports betting — calibration vs. accuracy (ScienceDirect)](https://www.sciencedirect.com/science/article/pii/S266682702400015X) — model calibration matters more than accuracy; overconfidence in sparse data regions
- [Methodology and evaluation in sports analytics — ML (Springer Nature 2024)](https://link.springer.com/article/10.1007/s10994-024-06585-0) — dependencies in data partitioning, contextual factors, trust through confidence scoring
- [Footballguys — Dynasty Investor: Rookie Pick Valuation (2024)](https://www.footballguys.com/article/2024-dynasty-investor-rookie-pick-valuation) — dynamic pick pricing, calendar effects, standing-dependent value
- [Dominican University — Cognitive Biases in Fantasy Football](https://www.dominican.edu/news/news-listing/professor-students-examine-how-cognitive-biases-shape-fantasy-football) — endowment effect, recency bias, anchoring in fantasy decision-making

---
*Pitfalls research for: Dynasty fantasy football front office OS*
*Researched: 2026-03-11*
