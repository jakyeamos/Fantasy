# Phase 5: Trade Intelligence - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the trade intelligence system: a 7-dimension trade evaluator, reroute path surfacer, and package builder. The evaluator explicitly distinguishes market-fair trades from strategically advancing ones. The package builder grows out of evaluation — it is not a standalone tool. Manager profiles (Phase 4) and player values (Phase 2) are consumed here — not extended. Dynamic pick valuation (Phase 6) is out of scope; picks are evaluated using Phase 2 baseline values.

</domain>

<decisions>
## Implementation Decisions

### Trade input
- **D-01:** Player-anchored input — user searches and adds players/picks freely to each side; not roster-browse-only
- **D-02:** Up to 3 parties supported — user assigns assets to each team's send/receive sides; evaluation always scores from the user's team perspective
- **D-03:** Pick identity matters — picks are entered as specific picks by owner (e.g., "Mike's 2026 1st"), not abstract tiers; projected draft slot is surfaced per pick
- **D-04:** Trade evaluator is launchable from multiple entry points: manager dossier, league drill-in, and standalone

### Evaluation output
- **D-05:** No composite verdict — 7 sub-scores are shown; user forms their own conclusion
- **D-06:** Strategic vs. market-fair distinction (TRADE-04) is a prominent separate callout banner — not buried in a low direction-fit sub-score. Example: "Market fair — but moves you away from your rebuild"
- **D-07:** Low-confidence dimensions show an inline `(low confidence)` label with muted text color on the dimension row — not a separate caveat section
- **D-08:** Evaluation output has an explicit "See reroutes" affordance as the natural next action after reading scores

### Reroute paths
- **D-09:** Two reroute types surfaced: (1) better-value target at the same position as the player being acquired, and (2) better package for the same target
- **D-10:** Maximum 3 reroutes — enough signal without noise
- **D-11:** Each reroute shows one-line reasoning explaining why it's a better option
- **D-12:** Reroutes live in a slide-in panel triggered by "See reroutes" — not a separate tab or page

### Package builder
- **D-13:** Package builder is not a standalone tool — it is triggered from the trade evaluation screen after scoring
- **D-14:** Manager-specific personalization is the default output — Phase 4 manager profile is applied automatically; no toggle required
- **D-15:** Two distinct offer structures: aggressive open (what you could get away with) and fair close (genuinely balanced) — not a single midpoint
- **D-16:** Output is screen-readable only — user executes manually in Sleeper; no copy/export functionality needed

### Claude's Discretion
- Exact scoring formula per dimension (weights, normalization approach)
- How to handle trades where the counterparty is not in the user's league (hypothetical trades)
- Specific slide-in panel component choice (shadcn Sheet vs. custom drawer)
- How to display pick slot projections in the input (inline badge vs. tooltip)
- Route structure for the trade evaluator (e.g., `/league/:leagueId/trades/new` or standalone `/trades`)

</decisions>

<specifics>
## Specific Ideas

- The primary use case is proactive/exploratory — "what would it take to get Player X" — not reactive (evaluating an offer already received). The input UX should optimize for building a trade from scratch, not reviewing a proposed one.
- The "strategic vs. market-fair" banner is the most important single output. A trade being fair doesn't mean it's right. This needs to be impossible to miss.
- Three-way deal support is intentional — multi-party trades are real and the player-anchored input handles them naturally. Evaluation always scores from the user's perspective regardless of party count.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Trade engine requirements
- `.planning/REQUIREMENTS.md` §Trade Engine — TRADE-01 through TRADE-04 (7 dimensions, reroute paths, package builder, strategic distinction)
- `.planning/ROADMAP.md` §Phase 5 — goal, success criteria, dependency on Phase 4

### Data sources (inputs to trade engine)
- `.planning/phases/02-team-intelligence/02-00-PLAN.md` §interfaces — DDL for `player_values`, `team_directions`, `team_scorecards` — primary inputs to all 7 evaluation dimensions
- `.planning/phases/02-team-intelligence/02-RESEARCH.md` — direction label definitions, DIRECTION_WEIGHTS — needed for direction fit dimension and strategic distinction banner
- `.planning/phases/04-manager-profiling/04-CONTEXT.md` — manager profile schema, pitch angle structure, exploitability score — consumed by package builder for manager-specific personalization

### Phase 3–4 UI patterns (for frontend consistency)
- `.planning/phases/03-core-dashboard/03-UI-SPEC.md` — spacing scale, typography, color tokens, component inventory
- `.planning/phases/04-manager-profiling/04-UI-SPEC.md` — dossier tab patterns, badge components, LOW CONFIDENCE banner treatment — trade evaluator follows same design language

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/src/fantasy/main.py`: FastAPI app factory — new `/trade` router plugs in via `app.include_router()`
- `backend/src/fantasy/routers/deps.py`: Dependency injection pattern for DB connection — trade router follows same pattern
- `backend/src/fantasy/intelligence/models.py` (Phase 2): `PlayerValue`, `DirectionResult`, `TeamScorecard` — primary inputs to trade dimension scoring
- `backend/src/fantasy/profiling/models.py` (Phase 4): `ManagerProfile`, `PitchAngle` — consumed by package builder for manager personalization

### Established Patterns
- `profiling/` package structure from Phase 4 — `trade/` package follows same layout: `__init__.py`, `constants.py`, `models.py`, `trade_engine.py`, `trade_repo.py`
- DuckDB query pattern from `league_repo.py` and `profiling_repo.py` — trade repo uses same connection approach
- Router registered in `main.py` via `app.include_router()` — `/trade` router follows this pattern
- Inline confidence labeling pattern established in Phase 4 (LOW CONFIDENCE banner, muted styling) — trade dimension confidence follows same visual treatment

### Integration Points
- `player_values` table (Phase 2) — trade engine reads values per player per league for all 7 dimensions
- `team_directions` table (Phase 2) — used to compute direction fit score and drive strategic distinction banner
- `manager_profiles` table (Phase 4) — package builder reads this to generate manager-specific opening offer
- Frontend: dossier page and league drill-in need "Evaluate Trade" entry points added; standalone route also needed

</code_context>

<deferred>
## Deferred Ideas

- Dynamic pick values in trade evaluation — Phase 6 replaces Phase 2 baseline pick values once standings-aware pick engine is built
- Manager-specific pitch notes as a standalone feature (TRADE-V2-01) — v2 backlog; Phase 5 already applies manager profile to package builder by default
- Saving/bookmarking evaluated trades for later review — not in Phase 5 scope
- Receiving an offer from Sleeper and auto-populating the evaluator — Sleeper API is read-only; manual input only

</deferred>

---

*Phase: 05-trade-intelligence*
*Context gathered: 2026-03-21*
