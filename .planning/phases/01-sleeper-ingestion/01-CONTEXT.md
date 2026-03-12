# Phase 1: Sleeper Ingestion - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the full data ingestion pipeline: fetch data from the Sleeper API and nfl_data_py, store it locally, surface data gaps explicitly, and allow manual correction of any ingested value. Analysis engines, team scorecards, and the dashboard UI are out of scope for Phase 1.

</domain>

<decisions>
## Implementation Decisions

### Storage Backend
- SQLite as the database — local file, zero setup, fits a single-user personal tool
- Alembic for schema migrations — schema changes must be versioned and reversible
- Database file lives in the project `data/` directory
- All leagues stored in shared tables with a `league_id` column — no per-league schema isolation

### Ingest Trigger
- On-demand only — user triggers a refresh; no background scheduler in Phase 1
- Expected refresh cadence: daily or less (Sleeper data changes infrequently between waivers/transactions)
- Incremental ingest from the start — track state via timestamps/cursors and only fetch changes; correctness-motivated, not a performance shortcut
- App is locked during ingest — reads are unavailable while an ingest run is in progress (acceptable given short ingest duration)

### Scoring History
- Use nfl_data_py (not Sleeper's deprecated player stats endpoint) for historical player-level stats
- Ingest all available seasons from nfl_data_py (10+ years) — this intentionally seeds Phase 8's Historical Prospect Lab, avoiding a large retroactive ingest later
- Reconstruct fantasy points from raw stat lines using each league's actual scoring settings (PPR, TEP, superflex, etc.) — scoring is computed per-league, not as a generic value
- Also ingest points for/against from Sleeper's standings endpoint (team-level PF/PA, available without the deprecated stats endpoint)

### Global Asset Baseline
- Seeded from two sources: ADP signals (Sleeper ADP or public dynasty ADP source) + nfl_data_py scoring reconstruction
- Baseline is foundation-only in Phase 1 — Phase 2 applies league-specific adjustments and direction weighting on top of it

### Health Check & Gap Surfacing
- Any data gap is shown as an explicit named label with explanation and estimated resolution phase
- Format: "[Gap name]: [Why it's missing]. Expected resolution: Phase X."
- Silent data drops are not acceptable — gaps surface, they do not disappear

### Claude's Discretion
- Manual correction model: how user overrides persist and survive re-ingestion (override table vs. correction log, conflict resolution strategy)
- Exact Alembic migration naming conventions and folder structure
- nfl_data_py data refresh cadence relative to Sleeper ingest cadence (historical data refreshes differently from live league data)
- Stack scaffold structure (Python package layout, FastAPI vs Flask, monorepo vs separate backend/frontend dirs)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project, no existing code

### Established Patterns
- None established yet — Phase 1 sets the foundation patterns for all subsequent phases

### Integration Points
- SQLite `data/` database is the primary integration point for Phase 2 (Team Intelligence) — all ingested data feeds the scoring and valuation engines
- nfl_data_py historical data (all seasons, per-league fantasy point reconstruction) feeds Phase 2's team scorecard sub-scores and Phase 8's Historical Prospect Lab backtesting

</code_context>

<specifics>
## Specific Ideas

- Incremental ingest is correctness-motivated — the goal is to track state properly from day one rather than retrofitting cursors/timestamps later
- 10+ years of nfl_data_py data is intentionally ambitious: collecting it in Phase 1 avoids a large retroactive ingest when Phase 8 needs it
- Fantasy point reconstruction must apply each league's specific scoring config (not a generic PPR/non-PPR split) — per-league accuracy is the point of this system

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-sleeper-ingestion*
*Context gathered: 2026-03-11*
