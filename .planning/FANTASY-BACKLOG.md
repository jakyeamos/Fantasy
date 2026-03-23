# Fantasy-Specific Backlog

**Defined:** 2026-03-22
**Purpose:** Convert fantasy-football-specific gaps into execution-ready tasks for a personal local dynasty tool. These are cross-cutting enhancements that improve trust and utility but are not yet sequenced into the numbered phase roadmap.

## Priority Bands

- **P1 — Weekly leverage:** Improves decisions you are likely to make in active leagues right now
- **P2 — Seasonal leverage:** Improves offseason, rookie-draft, and portfolio planning
- **P3 — Format breadth:** Expands support for edge-case league formats and one-off workflows

---

## FS-01: Draft Order Rules Engine

**Priority:** P1
**Goal:** Stop treating rookie pick value as simple inverse standings when the league actually uses max PF, lottery rules, playoff-team ordering rules, or custom tiebreakers.

**Actionable tasks:**
- Audit the current pick engine, dashboard copy, and draft-room logic for every place that assumes inverse standings by default.
- Define a `LeagueDraftOrderRule` model that captures non-playoff order basis, playoff-team order basis, lottery slots/odds, tiebreakers, and consolation or toilet-bowl exceptions.
- Add a per-league manual rule editor for draft-order settings that Sleeper does not expose cleanly.
- Update pick valuation and projected draft-slot calculations to use the stored draft-order rule set.
- Show the active rule explanation anywhere a projected pick value appears.
- Add regression fixtures for common dynasty setups: inverse standings, max PF for non-playoff teams, lottery top four, and playoff teams ordered by finish.

**Done when:** Pick projections explicitly cite the active draft-order rule set and produce correct slots under each supported fixture.

---

## FS-02: Contender Reality / Lineup Strength Modeling

**Priority:** P1
**Goal:** Distinguish a strong roster in abstract from a lineup that can actually win a title in the current format.

**Actionable tasks:**
- Build an optimal-starting-lineup calculator using each league's real lineup constraints.
- Compute starter strength by position against replacement-level baselines.
- Add bench-to-starter dropoff and injury fragility metrics so depth is evaluated in terms of actual weekly lineup risk.
- Create a title-window score that weights elite starter ceiling, lineup stability, and playoff-usable depth more heavily than raw roster value.
- Feed lineup-based signals back into team direction, trade evaluation, and dashboard summaries.
- Add validation cases from real contender, fake contender, and productive-struggle rosters.

**Done when:** Team labels and trade recommendations can explain lineup-level reasons, not just aggregate roster-value reasons.

---

## FS-03: Dynasty Calendar Mode

**Priority:** P1
**Goal:** Make recommendations change with the dynasty calendar instead of acting as if March, August, November, and rookie-draft week are strategically identical.

**Actionable tasks:**
- Define named dynasty calendar states: startup draft, preseason, early season, trade-deadline window, playoffs, rookie fever, post-combine, post-NFL Draft.
- Create a calendar-state service that auto-selects the current state but allows manual override.
- Add state-aware weighting rules for veterans, future picks, current rookies, productive-struggle moves, and liquidation moves.
- Update trade, pick, rookie-board, and dashboard recommendation text to cite the active calendar state.
- Add tests that confirm the same asset receives different guidance in different calendar windows.

**Done when:** Recommendation changes across the year are intentional, visible, and attributable to an explicit calendar state.

---

## FS-04: Roster Management Layer

**Priority:** P1
**Goal:** Cover the everyday dynasty decisions that happen below the trade layer: stash, cut, taxi, IR, and consolidation.

**Actionable tasks:**
- Model taxi eligibility, taxi occupancy, IR occupancy, and any manual exceptions per league.
- Build a stash score for end-of-bench and taxi-eligible players.
- Build a cut-candidate score that identifies low-upside cloggers and replaceable roster spots.
- Add consolidation suggestions that flag when two or three marginal pieces should be packaged into one better asset.
- Add a roster-hygiene panel to each league view with stash, cut, move-to-taxi, and consolidate suggestions.
- Add human-verification examples from your current leagues so the output reflects how you actually manage the last five roster spots.

**Done when:** Every team screen includes actionable low-level roster moves beyond trades and draft picks.

---

## FS-05: Waiver / FAAB Intelligence

**Priority:** P2
**Goal:** Turn waivers from an external manual habit into a first-class dynasty workflow.

**Actionable tasks:**
- Verify which waiver and FAAB settings Sleeper exposes directly and list gaps that require manual entry.
- Add manual inputs for remaining FAAB, waiver cadence, and any league-specific roster-churn rules if the API is incomplete.
- Build a watchlist engine for contingent-value backs, injury openings, post-draft rookie fallers, backup QBs in superflex, and depth-chart climbers.
- Generate bid-range suggestions tied to team direction, remaining budget, and urgency.
- Add a light feedback loop so previously recommended waiver adds can be reviewed later.

**Done when:** The app can tell you who to add and what range to bid, or explicitly tell you that a player is only worth a free post-waiver add.

---

## FS-06: Manager Rookie / Pick Market Profiles

**Priority:** P1
**Goal:** Extend manager profiling into rookie-draft and pick-market behavior, not just completed trade history in the abstract.

**Actionable tasks:**
- Mine historical rookie-draft selections for positional preference, early-vs-late pick aggression, and repeated archetype bets.
- Score each manager's willingness to pay a premium for early firsts, second-round dart throws, and draft-day trade-ups.
- Detect whether a manager prefers ceiling bets, age-adjusted production, landing-spot hype, or "safe" profiles.
- Feed these tendencies into package builder, reroute suggestions, and draft-room warnings.
- Add low-confidence suppression when historical rookie-draft evidence is too thin.

**Done when:** Trade and draft views can say which manager is most likely to buy a certain pick or prospect profile and why.

---

## FS-07: League Rule Support Matrix

**Priority:** P1
**Goal:** Make unsupported or partially supported league settings explicit so the app never gives quiet bad advice.

**Actionable tasks:**
- Enumerate supported, partially supported, and unsupported league rules that materially change dynasty value.
- Add a league scanner that flags formats such as IDP, devy, salary cap, contracts, best ball, empire, median wins, points per first down, return-yard scoring, and multiple TE-premium variants.
- Define fallback behavior for partially supported rules and require manual acknowledgment where recommendations may be distorted.
- Show a league-level warning banner when a rule set falls outside the trusted support matrix.
- Prioritize which unsupported formats are worth implementing based on your real leagues and near-term league plans.

**Done when:** No connected league silently receives high-confidence advice under rules the tool does not actually model.

---

## FS-08: NFL Context Freshness

**Priority:** P1
**Goal:** Make sure dynasty outputs react to football reality shifts such as injuries, free agency, rookie declarations, combine results, draft capital, and landing spots.

**Actionable tasks:**
- Define the freshness domains that materially change dynasty value: injuries, suspensions, depth-chart role changes, free agency, combine/pro-day inputs, rookie declarations, draft capital, and landing spots.
- For each domain, decide whether the source is automated, manually entered, or intentionally unsupported.
- Tag recommendation surfaces with freshness metadata and stale-state warnings.
- Add recompute triggers for major football events such as the NFL Draft and major injury news.
- Add a manual override or notes path for football context changes that are not yet automated.

**Done when:** Stale football context is visible and major NFL events trigger an intentional refresh of affected outputs.

---

## FS-09: Startup Draft and Orphan Intake Workflows

**Priority:** P2
**Goal:** Support the two highest-leverage "new team" scenarios that are not well served by the current connected-league flow.

**Actionable tasks:**
- Add a startup-draft mode with startup pick valuation, trade-up/trade-down heuristics, and direction-aware build templates.
- Add an orphan intake checklist that evaluates age curve, pick capital, dead roster spots, lineup viability, and liquidation options.
- Generate an initial 30-day action plan for a newly connected team or orphan roster.
- Add manual data-entry paths where a league is not yet fully ingested but you still want strategic guidance.

**Done when:** A startup or orphan team gets a clear first-pass strategy instead of requiring the full live-league workflow first.

---

## FS-10: Portfolio Thesis Exposure

**Priority:** P2
**Goal:** Expand portfolio risk from duplicate-player tracking to the football ideas the portfolio is actually betting on.

**Actionable tasks:**
- Extend exposure tracking from player names to rookie classes, archetypes, age buckets, NFL teams, offenses, and strategic labels.
- Add concentration flags for thesis-level bets such as "too much of one rookie class" or "too many fragile contender rosters."
- Build diversification suggestions that recommend what kind of asset or roster direction would reduce exposure.
- Add trade-impact previews that show how a proposed move changes thesis exposure, not just player overlap.

**Done when:** Portfolio analysis explains what football bets you are overexposed to, not just which players show up in multiple leagues.

---

## Cross-Cutting Validation Tasks

**Priority:** P1
**Goal:** Keep fantasy-domain enhancements grounded in your real leagues instead of generic dynasty discourse.

**Actionable tasks:**
- For every backlog item above, collect at least three real league examples where the current tool gives incomplete or misleading advice.
- Record the expected output for each example before implementation starts.
- Add a human-verify checkpoint after each workstream that asks whether the output would have changed an actual league decision.
- Keep a running "false sharpness" log for cases where the app sounds confident but misses league-specific context.

**Done when:** Each new fantasy-specific enhancement is validated against real decisions, not just synthetic fixtures.
