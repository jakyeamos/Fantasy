# Phase 4: Manager Profiling - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the manager profiling engine: analyze leaguemate trade history to generate per-manager dossiers with exploitability scoring, exploitation type classification, and pre-computed pitch angles. Add a `/league/:leagueId/managers` route and wire dossier links into the Phase 3 exploit window rows. Analysis engines (Phase 2) and the dashboard (Phase 3) are consumed here — not extended. Phase 5's trade package builder will consume this phase's manager profiles for personalization.

</domain>

<decisions>
## Implementation Decisions

### Entry point and navigation
- **D-01:** Dossiers are accessible from two paths: (1) a dedicated `/league/:leagueId/managers` route listing all managers, and (2) the Phase 3 exploit window manager rows in the league drill-in become clickable links to the dossier
- **D-02:** The managers list view shows: manager name + team direction label + exploitability score (with evidence count always co-located, e.g., "74 | 14 trades") — no exploitation type on the list
- **D-03:** The managers list also shows the top 1 pitch angle per manager as a preview row beneath the score
- **D-04:** Route is league-scoped: `/league/:leagueId/managers` and `/league/:leagueId/managers/:managerId` — a manager in multiple leagues has separate dossiers per league

### Dossier layout
- **D-05:** Tabbed layout inside each dossier: three tabs — Overview | Trade History | Pitch Angles
- **D-06:** Overview tab contains: roster summary, likely direction (from Phase 2 DirectionResult), positional needs, exploitability score with evidence count, exploitation type(s), and aggregate trade stats
- **D-07:** Trade History tab contains: all trades involving this manager, grouped by recency, with value delta per trade surfaced
- **D-08:** Pitch Angles tab contains: 2–3 pre-computed pitch angles, each showing deal archetype label + what to send + what to avoid + one-sentence reasoning

### Exploitation type classification
- **D-09:** Primary + secondary type assignment — if evidence score for a second type clears a minimum threshold, both are labeled. The dossier shows primary type prominently, secondary type as a secondary badge
- **D-10:** Signal mapping per type:
  - **value-loss trader**: received less KTC/ADP value than sent on majority of trades (measurable value delta)
  - **timing-error trader**: sold during a player's value trough or bought at value peak relative to injury/performance timeline
  - **directionally-incoherent trader**: trades contradict their own direction label (e.g., selling picks while labeled a rebuilder, buying aging veterans while labeled hard-rebuild)
  - **archetype-specific overpayer**: routinely overpays for one asset category (e.g., always overpays for QBs, or for WRs coming off injury)
- **D-11:** Evidence shown as aggregate stats (e.g., "Lost value on 7 of 10 trades"), not individual trade callouts

### Pitch angles
- **D-12:** Pitch angles are pre-computed per dossier at profile build time — not generated on-demand for specific trade scenarios (that's Phase 5's job)
- **D-13:** Each pitch angle includes: deal archetype label + what to send + what to avoid + one-sentence reasoning. Example: "Win-now swap: Send your aging RB2 + 2026 1st. This manager overpays for high-floor veterans. Avoid: prospect-heavy packages — he trades them away within 6 months."
- **D-14:** 2–3 pitch angles per dossier; top 1 angle shown as a preview on the managers list

### Evidence floor (LOW confidence)
- **D-15:** Constant name: `MIN_TRADE_EVIDENCE_THRESHOLD = 10` — lives in `backend/src/fantasy/profiling/constants.py` alongside other Phase 4 constants
- **D-16:** Below threshold: dossier shown in full but a prominent LOW CONFIDENCE banner appears at the top of the Overview tab — "LOW CONFIDENCE — Based on N trades (minimum 10 for reliable profiling). Treat all conclusions with skepticism." Exploitability score is visually dimmed (muted text color, not accent color)
- **D-17:** Exploitability score is always displayed with evidence count co-located wherever it appears — list view, dossier header, Overview tab. Format: "Exploitability: 74 | 14 trades"

### Claude's Discretion
- Exact KTC/ADP value delta computation approach (research should inform this)
- Secondary type minimum threshold value (the % of primary evidence that triggers secondary label)
- Whether directional incoherence is computed against the manager's own stored direction label or inferred from their roster
- Specific Alembic migration number for Phase 4 tables (005 or 006 depending on Phase 3's migration count)
- Tailwind styling choices for LOW CONFIDENCE banner (destructive variant vs. warning amber)

</decisions>

<specifics>
## Specific Ideas

- The managers list is a quick-scan tool — direction + score + one pitch angle preview is enough to know who to target today. Full dossier is for when you've identified a target and want to execute.
- LOW CONFIDENCE dossiers should still be useful. Even with 5 trades, direction label + roster summary is actionable. The banner is a trust calibration signal, not a blocker.
- The archetype-specific overpayer type is the most league-specific one — it requires enough trade volume to see a pattern. It's likely the last exploitation type to emerge for most managers.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 4 requirements
- `.planning/REQUIREMENTS.md` §Manager Profiling — MGR-01 through MGR-04 (dossier content, exploitability score, pitch angles, exploitation types)
- `.planning/ROADMAP.md` §Phase 4 — goal, success criteria, hard gate dependency on Phase 3

### Data sources (inputs to profiling engine)
- `.planning/phases/01-sleeper-ingestion/01-CONTEXT.md` — `trades` table schema (INGEST-05), correction model, ingest_runs table
- `.planning/phases/02-team-intelligence/02-00-PLAN.md` §interfaces — DDL and field list for `team_directions` (DirectionResult) — used to detect directional incoherence
- `.planning/phases/02-team-intelligence/02-RESEARCH.md` — direction label definitions, DIRECTION_WEIGHTS, DIRECTION_MOVE_MATRIX — needed for directional incoherence signal

### Phase 3 UI patterns (for frontend consistency)
- `.planning/phases/03-core-dashboard/03-CONTEXT.md` — routing structure, component patterns, established shadcn usage
- `.planning/phases/03-core-dashboard/03-UI-SPEC.md` — spacing scale, typography, color tokens, component inventory (LeagueCard, ExploitWindow rows become clickable links in Phase 4)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/src/fantasy/main.py`: FastAPI app factory — new `/profiling` router plugs in via `app.include_router()`
- `backend/src/fantasy/routers/deps.py`: Dependency injection pattern for DB connection — profiling router follows same pattern
- `backend/src/fantasy/intelligence/constants.py` (Phase 2): DIRECTION_WEIGHTS, DIRECTION_MOVE_MATRIX — needed by directional incoherence classifier; profiling constants.py imports from intelligence constants
- `backend/src/fantasy/intelligence/models.py` (Phase 2): `DirectionResult` — used to read manager's direction label for incoherence detection

### Established Patterns
- `intelligence/` package structure from Phase 2 — `profiling/` package follows same layout: `__init__.py`, `constants.py`, `models.py`, `profiling_engine.py`, `profiling_repo.py`
- DuckDB upsert pattern from `league_repo.py` — profiling repo uses same connection/upsert approach
- Router registered in `main.py` via `app.include_router()` — `/profiling` router follows this pattern

### Integration Points
- `trades` table (Phase 1 INGEST-05) is the primary data source — all trade history lives here
- `team_directions` table (Phase 2) provides direction labels per team — needed for directional incoherence detection
- Phase 3 frontend: `ExploitWindowRow` components need `href` prop added pointing to `/league/:leagueId/managers/:managerId`
- New Phase 4 Alembic migration needed for `manager_profiles` and `manager_pitch_angles` tables

</code_context>

<deferred>
## Deferred Ideas

- Manager-specific pitch notes tailored to a specific trade target (TRADE-V2-01) — that's Phase 5's trade package builder with manager profile personalization
- On-demand pitch angle generation for a specific trade scenario — Phase 5
- Historical manager behavior comparison (how has their behavior changed over seasons) — not in Phase 4 scope

</deferred>

---

*Phase: 04-manager-profiling*
*Context gathered: 2026-03-21*
