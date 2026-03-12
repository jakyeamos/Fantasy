# Feature Research

**Domain:** Dynasty fantasy football personal intelligence OS
**Researched:** 2026-03-11
**Confidence:** HIGH (architecture and tool landscape), MEDIUM (gap analysis — confirmed by indirect evidence), LOW (competitor internal roadmaps)

---

## Existing Tool Landscape

Understanding what's already built is prerequisite to knowing what's table stakes vs differentiating.

| Tool | Core Value | Key Limitation |
|------|-----------|----------------|
| KeepTradeCut (KTC) | Crowdsourced player/pick values, liquidity scores, trade DB | All values locked to 12-team 0.5 PPR; no league-specific adjustment beyond Superflex/TEP toggles; no team direction, no manager profiling |
| FantasyCalc | Algorithmic values from real-trade volume; league sync, trade finder | Values are market consensus, not personalized to your team direction or league context |
| DynastyNerds / DynastyGM | League sync, trade calculator, league analyzer (premium), film room, NAS prospect scores, combine tracker | Direction labeling is manual; no manager behavior profiling; prospect research is analyst opinion, not backtested model |
| Dynasty Daddy | Free analytics, power rankings, portfolio exposure (cross-league), trade calculator | Values are generic; no team strategy layer; no manager dossiers; league context is surface-level |
| Sleeper built-ins | Waiver wizard, power ratings, trade calculator (via Dynasty Assistant integration) | Highly generic; no direction detection, no manager profiling, no pick engine, no prospect depth |
| StatChasers Rookie Hit Rates | Historical hit-rate buckets by position/round/format | Static lookup table — not integrated with your roster or direction; no comps engine |
| Draft Sharks | Multi-year projections, aging curves, format charts, prospect grades | Tool fragmentation; no personalized integration; dynasty feels secondary to redraft |

**Summary gap across all tools:** No tool integrates team direction detection, manager behavior profiling, league-specific value adjustment, dynamic pick valuation, and prospect research into a single opinionated recommendation layer. Every tool stops at data display. None tell you *what to do next* given your specific roster, league, and counterparties.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features every dynasty manager using this tool will expect. Missing these makes the product feel unfinished before they reach the differentiating features.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Sleeper league ingestion (rosters, picks, standings, settings) | This is the data foundation — nothing works without it | MEDIUM | Sleeper public API is well-documented and requires no auth for public leagues; complication is parsing all format variations |
| Player values with superflex and TEP adjustments | KTC and FantasyCalc both do this; managers now expect format-aware values as baseline | MEDIUM | Must treat SF/1QB and TEP as first-class toggles, not afterthoughts; affects every downstream output |
| Trade evaluator showing whether a trade is fair | Every tool has some form of this; managers won't trust a system without it | MEDIUM | This system's version must go beyond "Player A = X points, Player B = Y points" — include direction fit and roster fit |
| Roster power ranking / team scorecard within league | KTC power rankings, DynastyNerds league analyzer both do this; managers expect to see their team ranked | MEDIUM | Scorecard should decompose into sub-scores (win-now, future value, age, pick capital, depth) not just one opaque number |
| Pick valuations for future picks | Dynasty managers trade picks constantly; no pick value = incomplete trade tool | MEDIUM | At minimum: early/mid/late 1st, 2nd tiers by year; dynamic pick engine is a differentiator on top of this baseline |
| Rookie rankings and prospect profiles | Any serious dynasty tool covers the rookie class | LOW-MEDIUM | Table stakes for basic rankings; context-aware format adjustments are differentiating |
| Cross-league multi-team management | Dynasty Daddy has portfolio view; managers with 2+ leagues expect unified access | LOW | Basic multi-league view is table stakes; the intelligent portfolio layer (exposure flags, correlated risk) is differentiating |
| League snapshot / historical tracking | Managers want to see how their team has changed | MEDIUM | Even basic season snapshots satisfy this — continuous retrospectives are differentiating |
| Manual data correction support | Sleeper API data is sometimes incomplete (partial trade history, missing picks) | LOW | Required before launch — without fallback, incomplete data corrupts all analysis |

---

### Differentiators (Competitive Advantage)

These are where this system competes. No existing tool does all of these, and no existing tool integrates them.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Team direction detection with confidence score and reasoning | No tool detects and labels your team's optimal path (rebuild / contend / sell window / retool) with explicit reasoning and alternate paths — they show data and let you figure it out | HIGH | The core intelligence output; drives all downstream recommendations; must show sub-score inputs so manager can audit the label |
| Context-aware action items ("do X because your team is Y in this league") | Generic tools show data; this system generates ranked action items specific to your team's direction and league environment | HIGH | Hardest product problem — requires all other engines to be working first |
| Manager dossier per leaguemate (trade tendencies, exploitability, pitch angles) | No public tool builds per-manager behavioral profiles from transaction history | HIGH | Requires substantial trade/transaction history ingestion and pattern detection; one of the clearest gaps in the market |
| Trade pathing (surface reroute paths, package alternatives, pitch notes per manager) | Trade calculators show fairness; none show who else to target if the deal falls through or how to pitch based on counterparty psychology | HIGH | Depends on manager dossiers and team direction being functional |
| Package builder with fair range, best version, and manager-specific opening offer | Generic trade calculators show equal value; none tailor the opening offer to the specific counterparty's known tendencies | HIGH | Highest-leverage output for a negotiating manager; no competitor comes close |
| Dynamic pick valuation adjusted for class strength, standings, calendar timing, and active rebuilder count | Static pick charts exist everywhere; dynamic adjustments based on how many teams in your specific league are rebuilding, current class quality, and timing do not | HIGH | The insight that "your 1.04 is worth more in this league because only two teams are competing" is not available anywhere |
| Prospect research backed by historical hit-rate models (backtested, not just analyst opinion) | StatChasers does hit-rate buckets but isn't integrated; DynastyNerds has analyst film grades; no tool combines backtested position models with your specific format and draft capital inputs | HIGH | Requires historical database build (Phase 4); differentiating output is archetype clustering, hit-rate bands, and comps with confidence ranges |
| League-specific player values (adjusted for your format, roster construction, and direction) | KTC locks values to 0.5 PPR 12-team; FantasyCalc uses market consensus; neither adjusts values relative to your team's actual direction and positional needs | HIGH | E.g., "this RB is worth more to your roster than market says because you're thin at RB and contending" — direction-aware, roster-aware values |
| Recommendation retrospectives (were direction labels calibrated? did prospect tiers hit?) | No tool grades its own past recommendations; this builds manager trust and system credibility over time | MEDIUM | Requires snapshot history and outcome tracking; feasible after Phase 5 |
| Portfolio exposure dashboard with correlated risk flags | Dynasty Daddy has basic cross-league exposure; no tool flags correlated risk ("you have CMC on 3 of 3 teams during his injury window") | MEDIUM | Lower complexity than manager dossiers; high value for multi-league managers |

---

### Anti-Features (Deliberately NOT Building)

| Anti-Feature | Why Requested | Why Problematic | Alternative |
|--------------|---------------|-----------------|-------------|
| Public rankings aggregator / leaderboard | Feels like more data = more value | Turns the product into a content site, not an intelligence engine; requires ongoing editorial labor; directly competes with KTC/FantasyCalc on their home turf | Keep all outputs personal and league-specific; never publish consensus rankings |
| Automated trade offer sending | Managers want shortcuts | Sleeper's API is read-only for leagues (no trade submission endpoint); also removes human judgment from the final action, which is the right boundary for a recommendation tool | Produce trade package and pitch language — manager sends it manually |
| Film study / scouting replacement | Managers want a single source of truth | Data and film are complementary; claiming to replace film creates false precision and erodes trust when prospects bust | Flag where data signals agree or conflict with consensus; let manager layer in film |
| Full custom formula authoring in v1 | Power users want to tune every weight | Massive scope addition; creates maintenance burden; early-stage systems need to be opinionated to validate that the core model is useful before exposing knobs | Support manual corrections and notes everywhere; defer deep formula authoring to v2+ |
| Perfect point predictions / deterministic outcomes | Managers want certainty | Dynasty is inherently probabilistic; false precision damages trust harder than uncertainty acknowledgment; every tool that claims precision loses credibility on busts | Show confidence bands, hit-rate ranges, and "what could break this thesis" explicitly |
| Multi-platform ingestion (ESPN, Yahoo, MFL) in v1 | Managers want platform flexibility | Sleeper API is uniquely clean and free; adding platforms before core engines are validated creates coupling risk and fragmentation | Architect ingestion layer as abstracted so adding platforms later is mechanical, not a redesign; ship Sleeper first |
| Social/community features (trade forums, chat, public profiles) | Managers want community | Turns personal intelligence OS into a social network — entirely different product; no single-user competitive advantage in social features | This is a personal tool; opinionated private recommendations are the moat |
| Start/sit optimizer for weekly redraft lineups | Common feature request | This product is dynasty-focused, not weekly redraft; start/sit is heavily commoditized by FantasyPros, ESPN, etc.; adding it dilutes product identity | Scope explicitly excludes weekly redraft optimization; direct managers to existing tools for this |

---

## Feature Dependencies

```
[Sleeper Data Ingestion]
    └──required by──> [Team Scorecard]
    └──required by──> [Trade History Ingestion]
    └──required by──> [Roster Power Ranking]
    └──required by──> [Pick Valuations]

[Team Scorecard]
    └──required by──> [Team Direction Detection]
                          └──required by──> [Context-Aware Action Items]
                          └──required by──> [League-Specific Player Values]
                          └──required by──> [Trade Evaluator (direction fit)]

[Trade History Ingestion]
    └──required by──> [Manager Dossier]
                          └──required by──> [Trade Pathing]
                          └──required by──> [Package Builder (manager-specific offer)]

[Team Direction Detection]
    └──enhances──> [Pick Timing Recommendations]
    └──enhances──> [Package Builder]

[Historical Prospect Database]
    └──required by──> [Hit-Rate Models]
                          └──required by──> [Prospect Tiers with Confidence Bands]
                          └──required by──> [Archetype Clustering & Comps]

[Pick Valuations (baseline)]
    └──enhanced by──> [Dynamic Pick Engine (class strength, rebuilder count, timing)]

[League Snapshots]
    └──required by──> [Recommendation Retrospectives]
    └──required by──> [Manager Behavior Trend Persistence]

[Multi-League Support]
    └──required by──> [Portfolio Exposure Dashboard]
    └──required by──> [Cross-League Exposure Flags]
```

### Dependency Notes

- **Sleeper ingestion is the root dependency** for every analysis engine — it must be solid and handle edge cases (incomplete history, custom roster slots, partial picks) before anything downstream is reliable.
- **Team direction detection requires the full team scorecard** — you cannot label direction from a single metric; the sub-scores (age, pick capital, win-now, depth, fragility) must all be present.
- **Manager dossiers require meaningful trade history** — if a league is new or trade volume is low, dossiers will be sparse; system must handle thin-data gracefully with fallback states.
- **Dynamic pick engine enhances but does not replace** baseline pick valuations — the basic tier system (early/mid/late 1st/2nd by year) must exist before dynamic adjustments layer on top.
- **Recommendation retrospectives conflict with perfectionism** — building retrospectives requires accepting that early recommendations will be imprecise; this is a feature, not a bug; schedule Phase 5 after the core is validated.

---

## MVP Definition

### Launch With (v1 — Phase 1 + Phase 2)

Minimum viable product that proves the core thesis: context-aware recommendations beat generic rankings.

- [ ] Sleeper league ingestion (rosters, picks, standings, format settings) — no data, no product
- [ ] League-specific format flags (superflex, TEP, premium, non-standard lineup) — required from day one or values are wrong
- [ ] Team scorecard with sub-scores (win-now, future value, depth, pick capital, flexibility, fragility, age risk) — the foundation all direction detection sits on
- [ ] Team direction detection with confidence score, reasoning, and alternate paths — the primary thesis differentiator
- [ ] Roster power ranking within league — table stakes baseline; validates ingestion is working
- [ ] Trade evaluator (fairness + direction fit + roster fit) — proves the recommendation layer over generic calculators
- [ ] Manager dossier (trade tendencies, overpay patterns, pitch angles) — Phase 2 core differentiator; no other tool has this
- [ ] Dashboard: direction labels, top 3 action items per team, value risers/fallers, cross-league exposure alerts — the interface that makes the analysis actionable
- [ ] Basic pick valuations (early/mid/late tier by year) — required for trade evaluator to function on pick-heavy trades
- [ ] Manual correction support everywhere — required before launch; incomplete Sleeper data is real and must be handled

### Add After Validation (v1.x — Phase 3)

- [ ] Dynamic pick engine (class strength, rebuilder count, timing adjustments) — validates after basic pick valuations are confirmed accurate
- [ ] Rookie board with format-aware ranks, tiers, and roster-fit overlays — add once direction detection is validated
- [ ] Pick timing recommendations (sell / hold / use) — depends on dynamic pick engine + direction
- [ ] Package builder with manager-specific opening offers — add once dossiers have enough data to be reliable

### Future Consideration (v2+ — Phase 4 + Phase 5)

- [ ] Historical prospect database (10+ years, position models, archetype clustering) — high research value but requires significant data engineering; validate tool usefulness first
- [ ] Hit-rate models with backtested weights by position and archetype — depends on historical DB; Phase 4 is research-heavy infrastructure before any output is visible
- [ ] Recommendation retrospectives — requires Phase 1-3 to have been running long enough to produce outcomes worth grading
- [ ] Manager behavior trend persistence across seasons — requires multi-season transaction history; deferred until base dossiers are validated

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Sleeper data ingestion | HIGH | MEDIUM | P1 |
| Format flags (SF, TEP, premium) | HIGH | LOW | P1 |
| Team scorecard with sub-scores | HIGH | MEDIUM | P1 |
| Team direction detection | HIGH | HIGH | P1 |
| Trade evaluator (direction + fit aware) | HIGH | HIGH | P1 |
| Manager dossier | HIGH | HIGH | P1 |
| Dashboard with action items | HIGH | MEDIUM | P1 |
| Basic pick valuations | HIGH | LOW | P1 |
| Manual corrections support | HIGH | LOW | P1 |
| Roster power ranking | MEDIUM | LOW | P2 |
| Dynamic pick engine | HIGH | HIGH | P2 |
| Rookie board with format-aware tiers | HIGH | MEDIUM | P2 |
| Package builder (manager-specific offer) | HIGH | HIGH | P2 |
| Portfolio exposure dashboard | MEDIUM | MEDIUM | P2 |
| Historical prospect database | HIGH | HIGH | P3 |
| Backtested hit-rate models | HIGH | HIGH | P3 |
| Archetype clustering and comps | MEDIUM | HIGH | P3 |
| Recommendation retrospectives | MEDIUM | MEDIUM | P3 |

**Priority key:**
- P1: Must have for launch (Phases 1-2)
- P2: Should have, add when core is validated (Phase 3)
- P3: High ceiling but deferred until product-market fit is established (Phases 4-5)

---

## Competitor Feature Analysis

| Feature | KTC | DynastyNerds/DynastyGM | Dynasty Daddy | This System |
|---------|-----|------------------------|---------------|-------------|
| League ingestion | Partial (public league ID only) | Full (Sleeper, MFL, ESPN, etc.) | Full (multi-platform) | Sleeper-first, abstracted for future platforms |
| Format-specific values | Superflex/TEP toggles only; no full format adjustment | Premium rankings set by analysts | Uses KTC/DP values, no proprietary model | League-specific adjustment based on actual format and roster context |
| Trade evaluator | Value comparison only | Value + win-now/rebuild split | Multi-source values comparison | Value + direction fit + roster fit + manager exploit quality |
| Team direction detection | None | None (manual labeling only) | None | Automated detection with confidence score and sub-score breakdown |
| Manager behavior profiling | None | None | None | Per-leaguemate dossier with tendency, exploitability, pitch angles |
| Pick valuation | Static market consensus tiers | Static consensus adjusted by analysts | Pulls KTC values | Dynamic: adjusted for class, standings, rebuilder count, timing |
| Prospect research | Crowdsourced grades, Devy ranks | Film room, NAS scores, Nerd Scores | Basic prospect rankings | Backtested position models, hit-rate buckets, archetype clustering (Phase 4) |
| Opinionated action items | None — stops at data | Some trade suggestions (premium) | None | Ranked action items with reasoning per team per league |
| Portfolio/cross-league exposure | None | None | Basic player exposure view | Exposure dashboard with correlated risk flags |
| Recommendation retrospectives | None | None | None | Season-over-season grading of past direction labels and prospect tiers |

---

## Sources

- [KeepTradeCut FAQ — confirms scoring limitation (12-team 0.5 PPR baseline, Superflex/TEP as toggles)](https://keeptradecut.com/frequently-asked-questions)
- [KeepTradeCut About — crowdsourced trade DB, liquidity scores, power rankings feature set](https://keeptradecut.com/about)
- [DynastyNerds Tools page — full premium feature list including league analyzer, film room, combine tracker](https://www.dynastynerds.com/dynasty-tools/)
- [StatChasers Rookie Hit Rates — historical hit-rate buckets by position/round/format, only tool approaching backtested modeling](https://statchasers.com/rookie-hit-rates/)
- [Draft Sharks dynasty tools overview — multi-year projections, aging curves; fragmented toolset](https://www.draftsharks.com/kb/best-dynasty-tools)
- [Dynasty Daddy portfolio feature — cross-league exposure tracking](https://dynasty-daddy.com/fantasy-portfolio)
- [FantasyCalc league sync](https://fantasycalc.com/league/import)
- [DynastyNerds DynastyGM landing](https://www.dynastynerds.com/dynasty-gm-landing/)
- [Draft Sharks Superflex trade value chart — confirms format-specific value fragmentation](https://www.draftsharks.com/trade-value-chart/dynasty/superflex)

---
*Feature research for: Dynasty fantasy football personal intelligence OS*
*Researched: 2026-03-11*
