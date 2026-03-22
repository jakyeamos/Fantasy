# Phase 6: Dynamic Pick Valuation - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the dynamic pick valuation engine: compute pick values from current standings, draft proximity, class strength (placeholder), and league-specific rebuilder count. Adjust per-manager demand using direction labels and trade history. Surface timing recommendations (sell now / hold until rookie fever / use on the clock) with one-line reasoning per pick. This is an engine upgrade — no new UI page. Dynamic values replace the Phase 2 baseline wherever picks appear (trade evaluator, existing league views). Rookie class evaluation (Phase 7) and historical prospect models (Phase 8) are out of scope.

</domain>

<decisions>
## Implementation Decisions

### Class strength signal
- **D-01:** Class strength is a neutral placeholder in Phase 6 — all draft classes treated as neutral until Phase 7 wires in actual class evaluation
- **D-02:** No ADP proxy used for class strength — Phase 7 owns class evaluation; Phase 6 must design the signal hook so Phase 7 can plug in without engine changes

### Display surface
- **D-03:** No new picks page — Phase 6 is a pure engine upgrade
- **D-04:** Dynamic pick values surface wherever picks already appear: Phase 5 trade evaluator (replaces Phase 2 baseline), existing league views — no new routes or pages introduced

### Timing recommendations (PICK-03)
- **D-05:** Three timing states: sell now / hold until rookie fever / use on the clock
- **D-06:** Each timing rec shows label + one-line reasoning tied to the inputs that drove it (e.g., "Team trending down, sell before rookie fever inflates competition")
- **D-07:** Timing recs surface inline where picks are displayed — not a separate section

### Manager demand signals (PICK-02)
- **D-08:** Demand signals are fully derived — no manual override
- **D-09:** Two signal sources: (1) Phase 4 direction label (rebuilder = high demand, contender = low), (2) manager trade history premium pattern (consistent pick overpayer = elevated demand signal even if direction label is ambiguous)
- **D-10:** Both signals are combined into a single per-manager demand factor consumed by the pick valuation engine

### Claude's Discretion
- Exact formula for combining standings, draft proximity, rebuilder count, and demand signals into pick value
- Calendar timing decay curve (how value changes as rookie draft approaches)
- How to quantify "pick premium" from trade history (delta approach, frequency approach, or hybrid)
- How demand factor is normalized and weighted relative to other pick value inputs
- Specific Phase 7 hook interface for class strength injection

</decisions>

<specifics>
## Specific Ideas

- Phase 7 integration must be a first-class design constraint, not an afterthought. The class strength hook should be a named, typed input to the pick valuation formula — not a commented-out TODO. Phase 7 should be able to plug in without touching Phase 6 engine code.
- The timing recommendation is the most user-facing output. "Sell now" with no reasoning is useless — the one-line reason is what drives action.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Pick engine requirements
- `.planning/REQUIREMENTS.md` §Pick & Rookie Engine — PICK-01 through PICK-03 (dynamic valuation inputs, demand signals, timing recommendations)
- `.planning/ROADMAP.md` §Phase 6 — goal, success criteria, research flag for algorithm methodology

### Data sources (inputs to pick engine)
- `.planning/phases/01-sleeper-ingestion/01-CONTEXT.md` — picks table schema (INGEST-04), trade history table (INGEST-05) — primary raw inputs
- `.planning/phases/02-team-intelligence/02-00-PLAN.md` §interfaces — DDL for `standings`, `team_scorecards` — used for standings-based pick valuation
- `.planning/phases/04-manager-profiling/04-CONTEXT.md` — manager profile schema, direction label, trade history structure — demand signal sources

### Phase 5 integration (pick value upgrade target)
- `.planning/phases/05-trade-intelligence/05-CONTEXT.md` — D-03 (picks entered as specific picks by owner), D-19 (Phase 2 baseline currently used) — Phase 6 replaces that baseline
- `.planning/phases/05-trade-intelligence/05-01-PLAN.md` — TradeRepo and trade models — pick value lookup is called here; Phase 6 replaces the value source

### UI patterns (for frontend consistency)
- `.planning/phases/03-core-dashboard/03-UI-SPEC.md` — spacing scale, typography, color tokens
- `.planning/phases/05-trade-intelligence/05-UI-SPEC.md` — pick display patterns in trade evaluator — Phase 6 upgrades these in place

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/src/fantasy/main.py`: FastAPI app factory — new `/picks` router plugs in via `app.include_router()`
- `backend/src/fantasy/routers/deps.py`: Dependency injection pattern for DB connection — pick router follows same pattern
- `backend/src/fantasy/intelligence/models.py` (Phase 2): `TeamScorecard`, `DirectionResult` — standings and direction label inputs to pick valuation
- `backend/src/fantasy/profiling/models.py` (Phase 4): `ManagerProfile` — direction label + trade history premium pattern for demand signals
- `backend/src/fantasy/trade/models.py` (Phase 5): `TradedPick` — pick identity model already defined; Phase 6 adds dynamic value to it

### Established Patterns
- `trade/` package structure from Phase 5 — `picks/` package follows same layout: `__init__.py`, `constants.py`, `models.py`, `pick_engine.py`, `pick_repo.py`
- DuckDB query pattern from `league_repo.py` and `trade_repo.py` — pick repo uses same connection approach
- Router registered in `main.py` via `app.include_router()` — `/picks` router follows this pattern
- Inline confidence/reasoning pattern from Phase 5 dimension rows — timing rec one-liner follows same visual treatment

### Integration Points
- `picks` table (Phase 1 INGEST-04) — current pick ownership per league per team
- `standings` table (Phase 1 INGEST-03) — team win/loss record drives standings-based pick value
- `manager_profiles` table (Phase 4) — direction label + trade premium pattern → demand factor
- Phase 5 trade evaluator: pick value lookup must be redirected from Phase 2 baseline to Phase 6 pick engine output
- Phase 7 hook: `class_strength` parameter in pick valuation formula must be a typed, injectable input — neutral float (0.0) in Phase 6, replaced by Phase 7

</code_context>

<deferred>
## Deferred Ideas

- Actual class strength evaluation — Phase 7 (Rookie Board) owns this; Phase 6 provides the hook
- Roster-fit filtered pick value (which pick is best *for this team* vs. best in abstract) — Phase 7 (PICK-05)
- Draft room view (best pick vs. trading the pick) — Phase 7 (PICK-06)
- Historical pick value backtesting — Phase 8

</deferred>

---

*Phase: 06-dynamic-pick-valuation*
*Context gathered: 2026-03-21*
