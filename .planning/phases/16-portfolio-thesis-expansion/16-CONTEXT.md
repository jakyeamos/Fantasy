# Phase 16: Portfolio Thesis Expansion - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Expand the existing portfolio exposure system from player-name tracking to thesis-level tracking across 6 dimensions: rookie classes, archetypes, age buckets, NFL teams, strategic labels, and a directional thesis layer. Add concentration flags inline on the portfolio page, diversification suggestions with trade engine CTAs, and a trade-impact preview inside the trade evaluator plus a standalone portfolio simulator. Does NOT include multi-season retrospective grading, prospect model retraining, or new player valuation models.

</domain>

<decisions>
## Implementation Decisions

### Thesis dimensions

- **D-01:** Ingest `years_exp` from Sleeper player detail endpoint and store on the `players` table. Use this field to derive rookie class grouping (draft year = current year − years_exp). Do not approximate from age.
- **D-02:** "Offenses" dimension is treated as NFL team (same proxy). No offensive scheme or play-caller data source exists — offenses and NFL teams are the same dimension in Phase 16.
- **D-03:** Strategic labels are player-level and derived automatically from existing Phase 2 component scores. Map score combinations to label buckets — e.g., high `ceiling` + low `floor_stability` = "Boom/Bust", high `insulation_value` + high `floor_stability` = "Floor Anchor", high `rerollability` = "Rebuild Stash". No new classification model required.
- **D-04:** Players with no `archetype_label` (non-prospects, QBs, veteran starters) are not silently skipped or given a fallback label. Instead, surface a flag in the portfolio UI prompting the user to rerun the Phase 8 prospect pipeline. The archetype dimension is omitted for that player until the pipeline runs.

### Concentration flags

- **D-05:** Concentration flags display inline within the existing exposure tables on the portfolio page — no separate "Thesis Flags" section. Each thesis dimension row (rookie class, archetype, age bucket, etc.) shows its tier inline.
- **D-06:** Threshold for thesis-level flags is `league_count >= 2` (reduced from the current player exposure threshold of 3). Concrete trigger examples: 4+ players from the same rookie class across 2+ leagues; 3+ players with the same strategic label across 2+ leagues.
- **D-07:** Flags are tiered: **Watch** / **Concern** / **Critical**. Thresholds per tier are Claude's discretion based on dimension count and league spread.
- **D-08:** Flags always show as long as the condition is true — no dismiss or snooze.

### Diversification suggestions

- **D-09:** Suggestions name specific players as targets (e.g., "Consider trading Marvin Harrison Jr. in League A to reduce 2023 class concentration"), not generic direction labels.
- **D-10:** Each suggestion includes a CTA that links to the trade engine pre-populated with the overexposed asset as the "give" side.
- **D-11:** Suggestions are scoped portfolio-wide, not per-league. The portfolio page surfaces the cross-league thesis risk; the suggestion addresses it at that level.

### Trade-impact preview

- **D-12:** Trade-impact preview lives inside the existing trade evaluator as a new "Portfolio Impact" section — not on a separate route.
- **D-13:** Preview is one-directional: shows only how the user's thesis exposure changes. Counterparty impact is not shown.
- **D-14:** A standalone portfolio impact simulator also lives on the `/portfolio` route, accessible without initiating a full trade evaluation.
- **D-15:** Both surfaces (trade evaluator section and portfolio simulator) use the multi-asset bundle format that matches the existing trade evaluator's asset input model.

### Claude's Discretion

- Exact tier thresholds (watch / concern / critical) for each dimension — use league count + asset count as inputs
- Strategic label bucket boundary values (which score ranges map to Boom/Bust vs. Floor Anchor vs. Rebuild Stash vs. other labels)
- UI layout of inline thesis rows within existing ExposureMatrix
- `years_exp` storage: add column to existing `players` table or new migration field

</decisions>

<specifics>
## Specific Ideas

- "Too many fragile contender rosters" as the canonical thesis-level concentration example (from roadmap success criterion 2)
- The diversification CTA should pre-populate the trade engine with the overexposed asset as the give side — not just link to a blank trade eval
- Standalone portfolio simulator uses multi-bundle format matching existing trade evaluator input, not a simple two-player picker

</specifics>

<canonical_refs>
## Canonical References

### Phase 16 requirements
- `.planning/ROADMAP.md` §Phase 16 — Goal, success criteria, dependency on Phase 15
- `.planning/REQUIREMENTS.md` §Portfolio & Memory (PORT-03, PORT-04) — Ownership tracking and portfolio-level risk requirements
- **Note:** FS-10 is cited in the roadmap as the requirement for this phase but is not yet formally defined in REQUIREMENTS.md. Researcher should flag this gap and define FS-10 from the roadmap success criteria before planning.

### Existing portfolio engine
- `backend/src/fantasy/portfolio/portfolio_engine.py` — Current `compute_exposure()` and `compute_correlated_risk()` methods; Phase 16 extends these
- `backend/src/fantasy/portfolio/portfolio_repo.py` — `_player_lookup()` queries `players` table for `player_id`, `full_name`, `position`, `team`; Phase 16 adds `years_exp`, `archetype_label`, `age` to this lookup
- `backend/src/fantasy/portfolio/models.py` — `ExposureRow`, `CorrelatedRiskRow`, `PortfolioExposureResponse`; new thesis dimension models extend these
- `backend/src/fantasy/portfolio/constants.py` — `CONCENTRATION_HEDGE_THRESHOLD = 3`; Phase 16 lowers thesis-dimension threshold to 2

### Direction labels (for directional thesis dimension)
- `backend/src/fantasy/intelligence/constants.py` — `CONTENDER_DIRECTION_LABELS`, `REBUILD_DIRECTION_LABELS`, `VALID_DIRECTION_LABELS`

### Prospect archetypes
- `backend/src/fantasy/prospects/models.py` — `archetype_label` field (str | None) on prospect features
- `backend/src/fantasy/prospects/prospect_repo.py` — Queries for `archetype_label` per player

### Phase 2 player scores (strategic labels source)
- `backend/src/fantasy/intelligence/` — Player component scores: `ceiling`, `floor_stability`, `rerollability`, `insulation_value` used to derive strategic label buckets

### Frontend
- `frontend/src/routes/portfolio.tsx` — Existing portfolio page with ExposureMatrix and CorrelatedRiskSection
- `frontend/src/components/ExposureMatrix.tsx` — Current inline exposure table; Phase 16 adds thesis dimension rows here
- `frontend/src/api/queries.ts` — `portfolioExposureOptions()` query; will need extended response type

### Schema
- `backend/alembic/versions/001_initial_schema.py` — `players` table definition (current columns: `player_id`, `full_name`, `position`, `team`, `age`, `metadata_blob`)
- Next Alembic migration number: **019** (018 is Phase 15 waiver/startup tables)
- Triple-write pattern required: new columns must appear in Alembic migration, `startup_tasks.py` `_SCHEMA_COMPAT_TABLES`, and `conftest.py` test schema bootstrap

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `PortfolioRepo._portfolio_roster_rows()`: already resolves the portfolio owner across all leagues — reuse as-is for thesis dimension queries
- `PortfolioRepo._player_lookup()`: extend to also return `age`, `years_exp`, `archetype_label` alongside existing `full_name`, `position`, `team`
- `ExposureRow` model: extend with thesis dimension fields rather than creating a parallel model
- Trade evaluator frontend: existing asset bundle input component can be reused for the portfolio simulator

### Established Patterns
- Triple-write schema: any new columns on `players` (e.g. `years_exp`) must be written to Alembic migration, `startup_tasks.py`, and `conftest.py`
- Adapter-first: Sleeper `years_exp` field mapping belongs in `SleeperMapper`, not in the engine or repo
- `CONCENTRATION_HEDGE_THRESHOLD` pattern in constants: add parallel `THESIS_CONCENTRATION_THRESHOLD = 2`

### Integration Points
- `SleeperMapper` → add `years_exp` mapping from Sleeper player detail
- `PortfolioEngine` → new `compute_thesis_exposure()` method (or extend `compute_exposure()`)
- Trade evaluator router → new `/trade/portfolio-impact` endpoint or extended trade response
- `/portfolio` route → add simulator panel below existing sections

</code_context>

<deferred>
## Deferred Ideas

- Offensive scheme / play-caller tagging as a distinct thesis dimension — no data source in Phase 16; revisit if Sleeper or a third-party API adds this
- Per-league suggestion scoping ("address it in League A first") — deferred; Phase 16 suggestions are portfolio-wide only
- Counterparty thesis impact in trade previews — deferred; Phase 16 preview is one-directional only
- Dismissable/snoozeable concentration flags — deferred; always-on in Phase 16

</deferred>

---

*Phase: 16-portfolio-thesis-expansion*
*Context gathered: 2026-03-30*
