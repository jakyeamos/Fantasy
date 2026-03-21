# Phase 3: Core Dashboard - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the first UI: a React dashboard that surfaces direction labels, value changes, cross-league exposure, and exploit windows per connected league. Wire in the snapshot table so no early state is lost before Phase 4 begins. Analysis engines (Phase 2) are consumed here — not extended. Manager behavior profiling (Phase 4) is out of scope, though the risers/fallers actionability filter anticipates it.

</domain>

<decisions>
## Implementation Decisions

### Main dashboard layout
- **D-01:** League cards tile in a 2–3 column grid (user runs 3 leagues)
- **D-02:** Each card shows: league name, direction label, confidence band (High / Medium / Low — not a %, not a bar), primary team weakness with actionable nudge (e.g., "Thin at WR2 — 2 tradeable picks")
- **D-03:** Direction label + confidence + primary weakness must be visible without scrolling or expanding — no collapsed sub-panels on the card face
- **D-04:** Clicking a card drills into a league-specific view (separate route, not a modal or accordion)

### Value risers/fallers (DASH-02)
- **D-05:** Time window is since last ingest run — not a fixed calendar window
- **D-06:** Show top 5 risers and top 5 fallers, displayed per league (same player appears once per league they're owned in — no deduplication across leagues)
- **D-07:** Each entry shows: player name, points delta (e.g., +8.2), and a reason string explaining the driver
- **D-08:** List is filtered by actionability — players whose owners don't trade are excluded; the goal is surfacing market inefficiencies, not a general info feed
- **D-09:** Phase 3 uses a placeholder heuristic for tradeability (e.g., recent transaction activity); Phase 4's manager behavioral data replaces this filter when available

### Exploit windows / behavioral triggers (DASH-04)
- **D-10:** Main dashboard shows the single top exploit window per league on the league card — not a separate section
- **D-11:** Full exploit window list lives inside the league drill-in view
- **D-12:** Within the drill-in, triggers are grouped by league, then collapsed per manager (one row per manager) with expand to see individual triggers
- **D-13:** Each trigger includes a suggested action (e.g., "Mike is panic-selling RBs — pitch him your RB2 for his WR1") — not observation-only
- **D-14:** If a manager shows multiple simultaneous triggers, they collapse into one "high opportunity" signal; the expand reveals all contributing triggers

### Snapshot mechanism (PORT-01)
- **D-15:** Snapshots are triggered automatically after every successful ingest run — no separate scheduler
- **D-16:** Ingest-triggered snapshots are delta-only (store changes since last snapshot); once per calendar month a full snapshot is taken
- **D-17:** Manual "snapshot now" trigger is available on both the main dashboard and inside each league's drill-in view
- **D-18:** Main dashboard shows last snapshot timestamp per league (e.g., "Last snapshot: 2 hours ago") — snapshots are not silent
- **D-19:** Snapshots are always full-portfolio — all connected leagues are snapshotted together, never one league at a time

### Claude's Discretion
- Visual design of the league card (spacing, typography, shadow treatment)
- Exact routing structure (e.g., `/dashboard` → `/league/:id`)
- Loading and error states for each dashboard section
- Snapshot delta format (which fields are stored as diff vs. full copy)
- Specific heuristic used for Phase 3 tradeability placeholder

</decisions>

<specifics>
## Specific Ideas

- The risers/fallers list is not an info feed — it's a market efficiency tool. If a player is surging but their owner never trades, that riser has no value to display. The filter is intentional product design, not a nice-to-have.
- The exploit window on the main card should feel like the most actionable thing visible at a glance — the one thing worth acting on today across each league.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Dashboard requirements
- `.planning/REQUIREMENTS.md` §Dashboard — DASH-01 through DASH-04 (card content, risers/fallers, cross-league exposure, exploit windows)
- `.planning/REQUIREMENTS.md` §Portfolio & Memory — PORT-01 (snapshot intervals and manual trigger)
- `.planning/ROADMAP.md` §Phase 3 — success criteria and HARD GATE note (direction label review before Phase 4)

### Phase 2 output tables (consumed by dashboard)
- `.planning/phases/02-team-intelligence/02-00-PLAN.md` §interfaces — DDL and field list for `team_scorecards`, `team_directions`, `player_values`
- `.planning/phases/02-team-intelligence/02-RESEARCH.md` — direction label definitions, confidence model, sub-score field names

### Phase 1 data (consumed by dashboard)
- `.planning/phases/01-sleeper-ingestion/01-CONTEXT.md` — league table schema, ingest_runs table (used to determine last-ingest time window for risers/fallers), correction model

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/src/fantasy/main.py`: FastAPI app factory with CORS — new dashboard and snapshot routers plug in via `app.include_router()`
- `backend/src/fantasy/routers/deps.py`: Dependency injection pattern for DB connection — all new routers should follow this pattern
- `backend/src/fantasy/db/models.py`: All Phase 1 table definitions — `leagues`, `rosters`, `standings`, `ingest_runs` are read by dashboard endpoints
- `backend/src/fantasy/intelligence/models.py` (Phase 2): `TeamScorecard`, `DirectionResult`, `PlayerValue` Pydantic models — dashboard serializes these to JSON responses

### Established Patterns
- Routers registered in `main.py` via `app.include_router()` — new `/dashboard` and `/snapshots` routers follow same pattern
- DuckDB upsert pattern from `league_repo.py` — snapshot writes use the same connection/upsert approach
- `ingest_runs` table tracks `completed_at` per league — risers/fallers use this as the "since last ingest" cursor

### Integration Points
- IngestService (`backend/src/fantasy/ingestion/ingest_service.py`) — needs a post-completion hook to trigger snapshot after successful ingest
- New `league_snapshots` table needed in a Phase 3 Alembic migration (005) — stores delta + monthly full snapshots keyed by league_id + timestamp
- Frontend bootstraps against the FastAPI backend; no existing frontend directory — Phase 3 creates it (React 19 / Vite / TanStack Query / shadcn+ui)

</code_context>

<deferred>
## Deferred Ideas

- Full behavioral tradeability filter for risers/fallers — requires Phase 4 manager trade history; Phase 3 uses a heuristic placeholder
- Historical snapshot comparison (side-by-side team state across time) — Phase 9 (PORT-02)
- Cross-league portfolio exposure dashboard (PORT-03, PORT-04) — Phase 9
- Top 3 quick-links per team on the main card (DASH-V2-01) — v2 backlog

</deferred>

---

*Phase: 03-core-dashboard*
*Context gathered: 2026-03-21*
