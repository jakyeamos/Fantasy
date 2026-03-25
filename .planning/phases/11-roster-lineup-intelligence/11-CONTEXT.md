# Phase 11: Roster & Lineup Intelligence - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

The system distinguishes a strong roster in abstract from a lineup that can actually win in the current format, and surfaces actionable low-level roster moves below the trade layer. This phase adds three distinct layers: (1) an optimal-starting-lineup calculator that scores each team's starter strength by position against replacement-level baselines; (2) a title-window label that feeds back into direction classification; and (3) a roster-hygiene panel that surfaces stash, cut, taxi, and consolidation suggestions per team. Weekly start/sit optimization is explicitly out of scope (dynasty-focused product; redraft optimization is commoditized elsewhere).

</domain>

<decisions>
## Implementation Decisions

### Replacement-level definition
- **D-01:** Replacement level is computed **per-league** from actual roster data — no global ADP baseline
- **D-02:** The replacement player at each position is the **weakest starter at that position across all teams in the league** (not the waiver wire) — this is the competitive floor a starter must beat to be meaningful
- **D-03:** **Flex slots** use the best available player regardless of position — no position-specific replacement for flex; the calculator picks the highest-value player who fits the slot
- **D-04:** Replacement level is **dynamic** — recomputed on each ingest cycle; weekly roster changes in the league update the baseline automatically

### Title-window score
- **D-05:** Title-window is expressed as a **label**, not a numeric score — labels are: "Peak Window," "Fading Window," "Outside Window" (exact strings TBD by Claude)
- **D-06:** **Starter ceiling is the primary weight** — a team with two elite WR1s and a top-5 QB scores higher than a team with broad depth and no ceiling pieces
- **D-07:** Title-window label lives in a **separate panel/card** from the existing scorecard — visually distinct, not a 10th scorecard dimension
- **D-08:** Title-window label **feeds back into the direction label engine** — a high win_now scorecard combined with a "Outside Window" title-window label nudges toward `fragile_contender` or similar; the exact integration point is Claude's discretion
- **D-09:** Title-window panel is visible on every team screen (league drill-in)

### Roster hygiene panel
- **D-10:** **Consolidate and cut get top billing** — they are the most-used action types; stash and move-to-taxi are present but secondary
- **D-11:** Cut candidates are evaluated on **two criteria, primary being roster slot constraint** ("this spot is blocking a better move") and secondary being low upside ("player has little dynasty value"); the slot-blocking framing should appear in the suggestion reasoning
- **D-12:** Consolidation suggestions **directly reference the trade evaluator** — each suggestion names specific players to package and a specific target from a named counterparty (e.g., "Package Player A + Player B → target Player X from Manager Y")
- **D-13:** Up to **5 suggestions per action type** — comprehensive, not curated to 1–2
- **D-14:** Suggestions reference `TradeEngine` / `PackageBuilder` output where available — no standalone consolidation engine; reuse Phase 5 infrastructure

### Taxi / IR eligibility modeling
- **D-15:** **Taxi eligibility is configured per-league** — some leagues follow standard Sleeper taxi rules, others have custom windows; a per-league taxi configuration block is required (similar to `LeagueDraftOrderRule` from Phase 10)
- **D-16:** **IR state is reflected from Sleeper as-is** — no IR move recommendations; no system suggestion to "move Player X to IR"; the user handles IR manually as part of market-cycle judgment
- **D-17:** Manual exceptions are **kept simple** — the system does not need to model mid-season eligibility overrides or complex house rules; basic per-league taxi config is sufficient
- **D-18:** Taxi/IR occupancy is surfaced as a **separate section** from the roster hygiene panel — it is informational slot accounting (how many taxi/IR spots are used vs. available), not a player-value judgment

### Claude's Discretion
- Exact label strings for title-window (e.g., "Peak Window" / "Fading Window" / "Outside Window" — or equivalent)
- Weight formula for the title-window classifier (starter ceiling is primary; lineup stability and playoff-usable depth are secondary)
- How title-window feeds into `DirectionEngine` — via scorecard input augmentation or as a post-classification adjustment
- Alembic migration numbering (must not conflict with 009–012 already in use)
- DB schema for per-league taxi configuration and lineup calculator outputs
- Whether `LineupEngine` and `HygieneEngine` are separate classes or combined in an `IntelligenceService` extension
- Exact threshold values that separate "Peak Window" / "Fading Window" / "Outside Window"

</decisions>

<specifics>
## Specific Ideas

- Consolidation suggestions are the most actionable output — they should feel like a mini trade recommendation, not a generic "consider trading these players." Referencing specific counterparty managers (from Phase 4 dossiers) is required.
- The cut-candidate framing should lead with the slot reason: "Cutting Player X frees a roster spot for a better waiver target" before mentioning the player's low dynasty value.
- Title-window panel should sit near the top of the team screen — it is a higher-signal summary than the detailed scorecard sub-scores.
- Taxi/IR section is a slot-accounting summary (e.g., "Taxi: 2/3 occupied — 1 spot available"), not a recommendation surface.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 11 requirements
- `.planning/FANTASY-BACKLOG.md` §FS-02 — full task breakdown for contender reality / lineup strength modeling (replacement-level baselines, title-window score, lineup signal feed-back)
- `.planning/FANTASY-BACKLOG.md` §FS-04 — full task breakdown for roster management layer (stash score, cut score, consolidation, hygiene panel, taxi/IR modeling)
- `.planning/ROADMAP.md` §Phase 11 — goal, success criteria (5 criteria), dependency on Phase 10

### Intelligence engines (primary integration targets)
- `backend/src/fantasy/intelligence/models.py` — `TeamScorecard` (9 dimensions), `DirectionResult`, `ScorecardInputs`; Phase 11 extends or augments these for lineup signals
- `backend/src/fantasy/intelligence/direction_engine.py` — `classify()` and `rank_moves()`; title-window label must feed into or adjust direction classification
- `backend/src/fantasy/intelligence/scorecard_engine.py` — reads `starters`, `bench`, `taxi`, `reserve` from DB; lineup calculator reads same data
- `backend/src/fantasy/intelligence/constants.py` — `DIRECTION_WEIGHTS` matrix; title-window integration point must respect existing weight structure

### Trade infrastructure (for consolidation suggestions)
- `backend/src/fantasy/trade/` — `TradeEngine`, `PackageBuilder`; consolidation suggestions reuse Phase 5 package-building logic to name specific targets and counterparties
- `backend/src/fantasy/profiling/` — manager dossiers; consolidation suggestions reference manager names and pitch angles from Phase 4

### Roster data
- `backend/src/fantasy/ingestion/sleeper_mapper.py` — `LeagueSettings` (roster_positions, superflex, taxi); `RosterSnapshot` (starters, bench, reserve, taxi fields); Phase 11 reads these directly
- `backend/src/fantasy/intelligence/scorecard_engine.py` lines 96–122 — shows how roster_positions and taxi are queried from DB; lineup calculator follows same pattern

### Phase 10 patterns (for per-league config)
- `.planning/phases/10-pick-accuracy-draft-order/10-CONTEXT.md` — D-01 through D-10; `LeagueDraftOrderRule` per-league config model is the pattern for Phase 11's per-league taxi configuration
- `backend/src/fantasy/repositories/league_repo.py` — league CRUD patterns; taxi config follows same approach

### Frontend (team screen)
- `frontend/src/routes/league.$leagueId.tsx` — existing team screen; title-window panel and roster-hygiene panel are added here; existing `LeaguePickList` and `ExploitWindowPanel` show card placement conventions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ScorecardInputs` model already carries `starters`, `bench`, `taxi`, `ir`, `roster_positions`, `weekly_fantasy_pts`, `position_medians` — the lineup calculator can consume this model directly without new ingestion work
- `PackageBuilder` (Phase 5) generates specific trade packages with target players and counterparty context — reuse for consolidation suggestions rather than building a new recommender
- `ValuationEngine.compute_all()` returns per-player value across 5 lenses — `comp_ceiling` is the existing ceiling signal the title-window classifier should weight

### Established Patterns
- Per-league config model pattern: `LeagueDraftOrderRule` (Phase 10) — taxi eligibility config follows the same structure (separate model, per-league, CRUD via `league_repo`)
- Direction label as string constant: all direction labels are string keys in `DIRECTION_WEIGHTS`; title-window label is a new orthogonal classification, not a new entry in that dict
- Engine isolation: each engine (`ScorecardEngine`, `DirectionEngine`, `ValuationEngine`) is a separate class injected into `IntelligenceService`; `LineupEngine` and `HygieneEngine` follow the same pattern

### Integration Points
- `IntelligenceService` is the orchestration layer — lineup and hygiene engines are wired in here, same as scorecard/direction/valuation
- `/intelligence` FastAPI router is the existing endpoint; Phase 11 extends or adds sub-routes for lineup scores and hygiene suggestions
- `league.$leagueId.tsx` frontend route is the team screen; new panels (title-window, hygiene) are added as new card sections below existing content

</code_context>

<deferred>
## Deferred Ideas

- Weekly start/sit optimizer — explicitly out of scope; dynasty-focused product
- IR move recommendations — user handles IR manually as market-cycle judgment (D-16)
- Complex mid-season taxi eligibility overrides / house-rule exceptions — kept simple per D-17
- Waiver wire watchlist and bid-range suggestions — Phase 15 (FS-05)

</deferred>

---

*Phase: 11-roster-lineup-intelligence*
*Context gathered: 2026-03-23*
