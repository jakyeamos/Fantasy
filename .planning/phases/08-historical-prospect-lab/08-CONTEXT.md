# Phase 8: Historical Prospect Lab - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the historical prospect database, position-specific backtested feature models, archetype clustering, and historical comps per prospect. Layer the outputs (tier, archetype label, comps, hit-rate bucket, risk band, over/undervalue flag) onto the existing Phase 7 rookie board cards — no new page or route. Phase 1 already ingested 10+ years of nfl_data_py data; Phase 8 transforms that raw data into model outputs. Current draft class only — historical data surfaces as comps per player, not as a browsable archive.

</domain>

<decisions>
## Implementation Decisions

### Hit definition (PROS-01, PROS-02, PROS-03)
- **D-01:** Hit = finished as top-X at their position for N seasons — threshold is position-specific, not a universal formula applied across all positions
- **D-02:** Three outcome buckets: **hit / mediocre / bust** — mediocre is a distinct bucket, not collapsed into miss
- **D-03:** Timing is NOT factored into the historical hit definition — a player who hits year 3 vs. year 1 counts identically in the historical record; timing matters for dynasty move decisions but not for defining precedent

### Historical comps (PROS-04)
- **D-04:** Three comps per prospect: **ceiling comp / median comp / floor comp** — labeled by outcome role, not ranked by similarity score
- **D-05:** Comp labels are framed **relative to ADP tier** — ceiling/floor mean "best and worst historical outcomes for a player taken at this draft capital tier," not absolute career outcomes
- **D-06:** Each comp displays: player name, outcome bucket (hit / mediocre / bust), and a **one-line reason** why the comp was matched (e.g., "similar draft capital, age, and target share profile") — peak stats are not shown
- **D-07:** Current class only — no UI for browsing the historical database directly; historical players surface only as named comps on current prospect cards

### Over/undervalue flags (PROS-05)
- **D-08:** Divergence stated as **direction + magnitude** — e.g., "ADP is 8 spots higher than historical precedent for this archetype suggests"
- **D-09:** One net verdict per prospect ("overvalued" or "undervalued") with **expandable per-signal sub-flags** — each diverging input (age, draft capital, production, testing) shows its own direction inline on expand
- **D-10:** When historical evidence is thin (below a minimum comp count), flag is shown with a **low-confidence label** — not suppressed entirely
- **D-11:** Flag is **descriptive only** — states the divergence, no suggested action or target round recommendation

### UI integration (Phase 7 layering)
- **D-12:** Phase 8 outputs layer onto the Phase 7 rookie board — existing `RookiePlayerCard` gains new fields; no new route or page
- **D-13:** Over/undervalue flag appears **both inline** (net verdict visible by default on the card) and in an **expandable section** (per-signal sub-flags visible on expand)
- **D-14:** View is **data-forward** — dense, sortable by model fields (tier, hit-rate bucket, ADP divergence magnitude); recommendation is visible but data is primary

### Claude's Discretion
- Exact position-specific hit thresholds (e.g., top-12 RB for 2+ seasons = hit; top-6 TE for 3+ seasons = hit)
- Exact mediocre band definition per position (the middle ground between hit and bust)
- Minimum comp count before low-confidence label triggers
- Feature set per position model (which subset of age, testing, production, market share, usage, draft capital are most predictive per position)
- Archetype clustering method and archetype vocabulary (label names and count per position)
- How comp similarity is computed (distance metric, feature weighting)
- Train/test split methodology for backtesting (time-based split specifics)

</decisions>

<specifics>
## Specific Ideas

- The over/undervalue flag is the highest-signal output in Phase 8 — it's the answer to "should I be paying current ADP for this player?" The direction + magnitude framing makes it actionable without prescribing a target round. "8 spots overvalued" is more useful than "overvalued."
- Three-bucket outcomes (hit/mediocre/bust) matter because "mediocre" is the most common dynasty outcome and collapsing it into "bust" distorts the hit rate. A player who produces for 4 years at RB2 level isn't a bust.
- Comp labels relative to ADP tier are important — a ceiling comp for a day-3 pick is very different from a ceiling comp for a 1.01. The framing "best case for this draft capital" is what makes comps useful for actual draft decisions.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Prospect lab requirements
- `.planning/REQUIREMENTS.md` §Prospect Lab — PROS-01 through PROS-05 (database scope, model inputs, threshold analysis, comps, over/undervalue flags)
- `.planning/ROADMAP.md` §Phase 8 — goal, success criteria, research flag (ML model selection and NFLverse ETL need research before planning)

### Data sources (already ingested in Phase 1)
- `.planning/phases/01-sleeper-ingestion/01-CONTEXT.md` — nfl_data_py ingestion approach (10+ years of raw stat lines already loaded); `players` table schema; `player_adp_baseline` table (ADP signals from FantasyPros dynasty ADP CSV)
- `.planning/ROADMAP.md` §Phase 1 open questions resolved — scoring reconstruction from nfl_data_py, ADP baseline seeding approach

### Phase 7 integration (layering target)
- `.planning/phases/07-rookie-board-draft-room/07-CONTEXT.md` — D-01 through D-04 (RookiePlayerCard fields already visible: name, position, archetype label, risk band) — Phase 8 adds comps, hit-rate bucket, over/undervalue flag to these same cards
- `.planning/phases/07-rookie-board-draft-room/07-UI-SPEC.md` — existing card layout, spacing tokens, color system — Phase 8 extensions must inherit these without introducing new design tokens

### Backend patterns
- `.planning/phases/06-dynamic-pick-valuation/06-CONTEXT.md` — engine package structure (constants, models, repo, engine) — prospect lab follows same layout
- `.planning/phases/04-manager-profiling/04-CONTEXT.md` — confidence labeling pattern (LOW confidence label, named threshold constant) — over/undervalue low-confidence treatment follows same approach

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/src/fantasy/main.py`: FastAPI app factory — `/prospects` router plugs in via `app.include_router()`
- `backend/src/fantasy/routers/deps.py`: DuckDB dependency injection — prospect router follows same pattern
- `backend/src/fantasy/intelligence/models.py` (Phase 2): `PlayerValue` Pydantic model — prospect model fields extend player identity already established here
- `frontend/src/components/trade/DimensionScoreRow.tsx`: Per-signal row with confidence label — over/undervalue sub-flag rows reuse this visual pattern (label + direction + magnitude + optional low-confidence tag)

### Established Patterns
- Engine package structure from Phase 6 (`picks/` package): `__init__.py`, `constants.py`, `models.py`, `engine.py`, `repo.py` — `prospects/` package follows same layout
- Low-confidence label pattern from Phase 4 (`MGR_MIN_TRADE_THRESHOLD` named constant, inline `(low confidence)` label with muted text) — prospect flag low-confidence treatment follows identical approach
- DuckDB query pattern from `league_repo.py` and `pick_repo.py` — prospect repo uses same connection approach
- shadcn `Badge` with variant for outcome bucket color coding — hit/mediocre/bust badges follow same usage as risk band badges in Phase 7

### Integration Points
- `players` table (Phase 1): player identity, position, draft year — primary key for linking historical stat lines to prospect profiles
- `player_adp_baseline` table (Phase 1): FantasyPros dynasty ADP — ADP divergence magnitude computed against this baseline
- Phase 7 `RookiePlayerCard` component: Phase 8 adds new props (comps array, hit_rate_bucket, overvalue_flag) — card component must be extended, not replaced
- Phase 7 `rookie_board_cache` table: Phase 8 may extend this table or add a `prospect_model_cache` table — planner to decide based on research
- New tables needed: `historical_prospect_stats` (processed feature vectors per player-year), `prospect_model_outputs` (current class model scores, comps, flags)

</code_context>

<deferred>
## Deferred Ideas

- Historical prospect archive browser (query any past prospect by name) — descoped; historical data surfaces as comps only, not as a browsable database
- Timing-weighted hit definitions (early breakouts scored higher) — explicitly excluded from historical model; timing is relevant for dynasty move decisions but not historical precedent
- Suggested action on over/undervalue flag (target round recommendation) — descriptive only in Phase 8; action-layer could be added in Phase 9 retrospectives if validated
- Cross-position hit rate comparisons (e.g., "WRs hit at 3x the rate of RBs at the same ADP") — interesting but not a Phase 8 requirement; deferred to backlog

</deferred>

---

*Phase: 08-historical-prospect-lab*
*Context gathered: 2026-03-22*
