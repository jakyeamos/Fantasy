# Phase 9: Portfolio & Retrospectives — Research

**Produced:** 2026-03-22
**Consumed by:** gsd-planner (Phase 9 plan decomposition)
**Phase requirements:** PORT-02, PORT-03, PORT-04, PORT-05, PORT-06

---

## User Constraints

> Copied verbatim from 09-CONTEXT.md. Planner MUST honor these without modification.

### Locked Decisions

**Navigation & entry points**
- D-01: Phase 9 gets a top-level Portfolio nav section — separate from the main dashboard and league drill-ins; this is the only cross-league view in the app
- D-02: Snapshot comparison is per-league — launched from inside the league drill-in, not from the Portfolio page
- D-03: Retrospectives have no dedicated route or view — grades compute in the backend, a health indicator is the only surface ("Last recalibrated: [date]")

**Snapshot comparison (PORT-02)**
- D-04: Snapshot selection uses event-anchored labels, not a raw date list — available anchors: trades (auto-labeled on execution), large roster changes (auto-labeled), start of season, end of season checkpoints
- D-05: View is delta-forward — one view showing what changed (direction arrows + magnitude), not a side-by-side two-column layout
- D-06: Player values show movement direction + magnitude (e.g., "WR1 ↓15 pts") — not raw historical numbers; players who left the roster since the snapshot still appear in the diff with a "traded/dropped" label
- D-07: Pick capital comparison uses the Phase 6 computed capital score — not a raw pick list diff; "Pick capital ↓22 pts" from Phase 6 dynamic valuation engine

**Portfolio exposure (PORT-03, PORT-04)**
- D-08: Concentration flag (PORT-03) outputs a recommendation hedge, not just a warning — e.g., "Cooper is on all 3 rosters — consider trading him in your most contending league to reduce exposure"
- D-09: Portfolio risk scope (PORT-04) is player cluster concentration only — directional thesis clustering and NFL schedule concentration are out of scope for v1
- D-10: Portfolio page shows a full breakdown — player x league exposure matrix; scannable but not collapsed by default
- D-11: Correlated NFL team risk is flagged — e.g., "You have CMC + Deebo + Aiyuk across 2 leagues — one 49ers collapse hits all three"; flagged alongside individual player concentration, not as a separate section

**Retrospectives (PORT-05, PORT-06)**
- D-12: No grades UI — direction label grades (PORT-05) and prospect tier grades (PORT-06) are backend-only; grades feed model recalibration, results are not surfaced to the user
- D-13: Recalibration runs once post-season when NFL outcomes are resolved — not dynamically updated during the season
- D-14: Minimum surface: a health indicator on a relevant view (e.g., Portfolio page or settings) — "Last recalibrated: [date]"; no calibration percentages, no per-call breakdown

### Claude's Discretion

- Exact threshold for "large roster change" auto-labeling a snapshot anchor (e.g., 3+ players changed in one ingest)
- Health indicator placement (Portfolio page footer, settings panel, or dashboard)
- Exposure matrix row/column layout and sort order
- How correlated team risk clusters are detected (shared NFL team affiliation on player records)
- Snapshot diff ordering (sort by magnitude of change, or by field type)

### Deferred Ideas (out of scope — do not plan)

- Directional thesis clustering ("all 3 teams are rebuild — if the draft class disappoints, all 3 lose") — PORT-04 scope is player cluster only in v1; thesis concentration is backlog
- NFL schedule concentration as a distinct portfolio risk signal (separate from correlated team exposure) — out of scope for v1
- Grades UI for retrospectives (calibration percentages, per-call breakdown, direction model accuracy report) — backend recalibration only in v1
- Suggested target round on snapshot comparison ("you could have sold WR1 here") — descriptive diff only, no prescriptive action layer
- Cross-league rookie board comparison — deferred; portfolio scope is roster exposure, not pick arbitrage across leagues

---

## What Phase 9 Actually Builds

Phase 9 is the final phase. It builds three distinct capabilities:

1. **Portfolio page** (`/portfolio`) — new top-level route with a player x league exposure matrix, concentration badges, hedge recommendations, and correlated NFL team risk rows. Read-only. No destructive actions.

2. **Snapshot comparison panel** — extends the existing `/league/$leagueId` drill-in by adding a "Compare to snapshot" button that opens an existing shadcn `Sheet` with event-anchored anchor selection and delta-forward diff display.

3. **Retrospective grading engine** — backend-only. Grades past direction labels (PORT-05) and past prospect tier assignments (PORT-06) against resolved outcomes. Health indicator ("Last recalibrated: [date]") is the only UI surface.

No new shadcn components are required (per 09-UI-SPEC.md). All design tokens are inherited.

---

## Standard Stack

All libraries are the project's established stack. No new dependencies are required for Phase 9.

### Core (backend)
| Library | Version | Purpose |
|---------|---------|---------|
| Python | 3.12 | Runtime |
| FastAPI | Existing | New `/portfolio` and `/snapshot-comparison` routers |
| DuckDB | 1.5.0 | All data reads — league_snapshots, rosters, players, team_directions, prospect_model_outputs |
| Pydantic v2 | Existing | Portfolio and retrospective domain models |
| Alembic | Existing | Two new migrations: one for portfolio tables, one for retrospective_runs |

### Core (frontend)
| Library | Version | Purpose |
|---------|---------|---------|
| React 19 | Existing | Portfolio page component tree |
| TanStack Router | Existing | New `/portfolio` route; Sheet panel inside existing league drill-in |
| TanStack Query | Existing | Four new query hooks with phase-appropriate stale times |
| shadcn/ui | Existing | All components already installed (card, badge, button, separator, skeleton, sheet, select) |
| Tailwind 4.2.2 | Existing | CSS-first config — no tailwind.config.js; all new classes use existing tokens |
| Lucide React | Existing | `AlertTriangle` (correlated risk rows), `Check` (matrix presence cells) — both already bundled |

### No new installations required
- No new shadcn components
- No new npm packages
- No new Python packages
- Confidence: HIGH (verified against 09-UI-SPEC.md and existing main.py, package.json not checked but no new deps needed)

---

## Architecture Patterns

### Backend package layout

Phase 9 follows the Phase 6 `picks/` package structure exactly, establishing a `portfolio/` package alongside it:

```
backend/src/fantasy/
├── portfolio/
│   ├── __init__.py
│   ├── constants.py          # SNAPSHOT_ROSTER_CHANGE_THRESHOLD = 3, concentration thresholds
│   ├── models.py             # ExposureRow, CorrelatedRiskRow, SnapshotAnchor, DiffRow, RetroGrade
│   ├── portfolio_engine.py   # Cross-league exposure computation, correlated cluster detection
│   ├── snapshot_diff_engine.py  # Anchor detection, event labeling, delta-forward diff computation
│   ├── retro_engine.py       # Direction label grading, prospect tier grading, recalibration run
│   └── portfolio_repo.py     # DuckDB reads from all upstream tables
├── routers/
│   ├── portfolio.py          # GET /portfolio/exposure, GET /portfolio/health
│   └── snapshot_diff.py     # GET /leagues/{league_id}/snapshot-anchors, GET /leagues/{league_id}/snapshot-diff
```

**Registration:** `main.py` adds `app.include_router(portfolio.router)` and `app.include_router(snapshot_diff.router)` following the existing pattern.

### Frontend structure

```
frontend/src/
├── routes/
│   └── portfolio.tsx           # NEW: /portfolio route
├── components/
│   ├── ExposureMatrix.tsx      # Custom HTML <table>, not shadcn Table
│   ├── CorrelatedRiskSection.tsx
│   ├── SnapshotComparisonSheet.tsx   # Uses existing Sheet component
│   ├── AnchorSelector.tsx      # Uses existing Select component
│   └── SnapshotDiffView.tsx    # Delta-forward diff rows
└── api/
    ├── queries.ts              # Four new TanStack Query option objects
    └── types.ts                # New TypeScript types for portfolio domain
```

**Route addition:** `portfolio.tsx` is a new TanStack Router file-based route. The `__root.tsx` nav must be extended with a "Portfolio" `<Link to="/portfolio">` entry.

### New database tables (two migrations)

**Migration 007 — portfolio tables:**

```sql
-- Portfolio exposure cache: cross-league player ownership matrix
-- Populated on demand (no background scheduler); computed fresh per API call
-- or cached and invalidated on ingest. Architecture decision: compute on-the-fly
-- from rosters table (simpler, always fresh) vs. cache table.
-- RECOMMENDATION: compute on-the-fly in Phase 9 (no cache table needed).
-- The rosters table already has all player_ids per league; a DuckDB cross-join
-- across leagues is fast enough. Cache table deferred to v2 if performance warrants.

-- retrospective_runs: recalibration run timestamps and metadata
CREATE TABLE IF NOT EXISTS retrospective_runs (
    id INTEGER PRIMARY KEY,
    run_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    run_type VARCHAR NOT NULL,           -- 'direction_labels' | 'prospect_tiers' | 'full'
    season VARCHAR NOT NULL,
    grades_json VARCHAR NOT NULL,        -- serialized grading results (backend-only)
    notes VARCHAR
);
```

**Migration 008 — Phase 8 output tables (if Phase 8 not yet run):**
Phase 8 defines `prospect_model_outputs` table. If Phases 7 and 8 are not yet executed, Phase 9 must not reference that table in live queries — the retrospective grading for PORT-06 should guard against a missing table or empty result set.

**Confidence: HIGH** (based on verified migration history: 001-006 exist, 007 and 008 are the next slots).

### Snapshot anchor detection pattern

The `ingest_runs` and `transactions` tables already exist (Phase 1). The snapshot anchor auto-labeling logic works as follows:

1. **Trade anchor:** A trade transaction (`type = 'trade'`, `status = 'complete'`) in the `transactions` table triggers auto-labeling. Each trade creates an anchor labeled "Trade — {date}" using the `created_at` timestamp.

2. **Roster change anchor:** When an ingest run completes and the delta snapshot records `len(changed_rosters) >= SNAPSHOT_ROSTER_CHANGE_THRESHOLD` (= 3), the snapshot is tagged as a roster-change anchor. The threshold is a named constant, not a magic number.

3. **Season checkpoints:** "Start of season" and "End of season" anchors are static labels attached to snapshots taken at known NFL calendar milestones. These can be derived from the `season` field on the `leagues` table and the NFL week calendar — a snapshot taken in week 1 is a reasonable "start of season" candidate.

4. **Anchor label format:** Backend generates formatted strings verbatim — frontend renders without transformation. Example: "Trade — Feb 14, 2026", "Season start — Sep 3, 2025".

The `league_snapshots` table already stores `snapshot_type`, `triggered_by`, and `payload_json` (which includes `delta.changed_rosters`). The anchor detection query reads from `league_snapshots` joined with `transactions` for the trade events.

### Cross-league exposure computation pattern

The `rosters` table stores `players` as a JSON-serialized list of player_ids per `(league_id, roster_id)`. The exposure matrix computation:

1. Parse `players` JSON for each roster row across all connected leagues
2. Normalize to a flat list of `(player_id, league_id)` pairs
3. Join against the `players` table for `full_name`, `position`, `team` fields
4. Group by `player_id` to count leagues and detect concentration (>= 2 or >= 3)
5. For Triple+ players, generate the hedge recommendation string (backend-provided verbatim)
6. For correlated NFL team risk: group players by `team` field across all owned rosters; flag any NFL team where the user owns 2+ players across 2+ leagues

This is a pure DuckDB query — no ML, no Phase 2 engine dependency. Confidence: HIGH.

### Delta-forward snapshot diff computation pattern

The diff between a current team state and a historical snapshot state requires:

1. Load the historical snapshot's `payload_json.state` for the target `league_id` from `league_snapshots`
2. Load current state from live tables (`team_directions`, `team_scorecards`, `player_values`, `traded_picks`)
3. Compute field-by-field deltas:
   - **Direction label:** string comparison — if changed, emit label transition string ("Productive Struggle → Retool")
   - **Scorecard sub-scores:** numeric delta per field; only emit if abs(delta) >= threshold
   - **Player values (`lens_market`):** delta per player in the user's roster; players who left emit departure type + last-known value
   - **Pick capital:** Phase 6 `capital_score` delta — requires querying the pick engine for current value vs. snapshot value. The snapshot already stores `traded_picks`; the pick engine can recompute capital score from historical pick state if needed, or the snapshot should store the capital score at time of snapshot.

**Critical finding:** The existing `SnapshotService._build_league_state()` stores `traded_picks` in the snapshot payload but does NOT store the Phase 6 `capital_score`. Phase 9 must either:
- (a) Store `capital_score` in future snapshots as part of the snapshot payload (requires modifying `SnapshotService` to call the pick engine), or
- (b) Recompute capital score from historical pick state using the Phase 6 engine at diff time

**Recommendation:** Option (a) — extend `SnapshotService._build_league_state()` to call the Phase 6 `PickEngine.compute_capital_score()` for each roster at snapshot time and store it in the payload. This avoids recomputation complexity and aligns with how other snapshot fields are stored. Phase 9 planning must include a task to patch `SnapshotService`. Confidence: HIGH.

### Retrospective grading pattern (PORT-05, PORT-06)

**Direction label grading (PORT-05):**
- Source: `team_directions` table — `primary_label`, `computed_at`, `league_id`, `roster_id`
- Outcome measurement: actual season win/loss record from `standings` table
- Grading logic: compare predicted label to season outcome — e.g., "True Contender" should correlate with top-half win rate; "Hard Rebuild" should correlate with bottom-half standings
- Output stored in `retrospective_runs.grades_json` — not surfaced in UI
- Run trigger: CLI script or admin endpoint, invoked manually post-season (D-13)

**Prospect tier grading (PORT-06):**
- Source: `prospect_model_outputs` table (Phase 8) — tier assignment at time of prediction, per player
- Outcome measurement: actual NFL performance from `player_stats_weekly` table (10+ years already ingested)
- Grading logic: compare predicted tier bucket (hit/mediocre/bust) against realized outcome using Phase 8 hit-rate definitions
- Output stored in `retrospective_runs.grades_json` — not surfaced in UI
- Guard: if `prospect_model_outputs` table does not exist (Phase 8 not run), grading returns empty result with a note

**Recalibration health indicator:**
- Query: `SELECT MAX(run_at) FROM retrospective_runs` — returns the most recent run timestamp
- If no rows exist: return `None`, frontend renders "Not yet recalibrated."
- Endpoint: `GET /portfolio/health` returns `{ last_recalibrated_at: datetime | null }`
- staleTime: 1 hour (per 09-UI-SPEC.md)

---

## Integration Points

### Upstream tables Phase 9 reads (all exist by Phase 9)

| Table | Source Phase | What Phase 9 Uses |
|-------|-------------|-------------------|
| `rosters` | Phase 1 | Cross-league player ownership (`players` JSON field, `league_id`) |
| `players` | Phase 1 | `full_name`, `position`, `team` for exposure matrix and correlated risk |
| `transactions` | Phase 1 | Trade events for snapshot anchor auto-labeling |
| `ingest_runs` | Phase 1 | Roster change events for anchor auto-labeling |
| `league_snapshots` | Phase 3 | Historical state for snapshot diff; anchor list |
| `team_directions` | Phase 2 | Direction label history for PORT-05 grading |
| `team_scorecards` | Phase 2 | Scorecard sub-score diff in snapshot comparison |
| `player_values` | Phase 2 | Player value diff in snapshot comparison (`lens_market`) |
| `standings` | Phase 1 | Actual season outcomes for direction label grading |
| `pick_values` (Phase 6 output) | Phase 6 | Capital score diff in snapshot comparison |
| `prospect_model_outputs` | Phase 8 | Tier assignments for PORT-06 grading (guard if table absent) |
| `player_stats_weekly` | Phase 1 | Realized NFL outcomes for PORT-06 grading |

### New tables Phase 9 creates

| Table | Purpose | Notes |
|-------|---------|-------|
| `retrospective_runs` | Stores recalibration run metadata and grades_json | Migration 007 |
| *(no exposure cache table)* | Exposure matrix computed on-the-fly from rosters | Simpler; cache deferred to v2 |

### Existing code Phase 9 modifies

| File | Modification |
|------|-------------|
| `backend/src/fantasy/snapshots/snapshot_service.py` | Extend `_build_league_state()` to store `capital_score` per roster in snapshot payload |
| `backend/src/fantasy/main.py` | Register two new routers: `portfolio.router`, `snapshot_diff.router` |
| `frontend/src/routes/__root.tsx` | Add "Portfolio" nav link alongside existing "Dashboard" and "Evaluate Trade" |
| `frontend/src/routes/league.$leagueId.tsx` | Add "Compare to snapshot" button + Sheet panel to league drill-in header |
| `frontend/src/api/queries.ts` | Add four new TanStack Query option objects |
| `frontend/src/api/types.ts` | Add TypeScript types for portfolio domain |

---

## Architecture Patterns (continued)

### DuckDB dependency pattern

All Phase 9 backend code follows the existing `deps.py` pattern:

```python
# backend/src/fantasy/routers/portfolio.py
from fantasy.routers.deps import get_conn

@router.get("/portfolio/exposure")
def get_exposure(conn: duckdb.DuckDBPyConnection = Depends(get_conn)):
    ...
```

Confidence: HIGH (verified by reading deps.py pattern used in all existing routers).

### Snapshot state payload structure (verified)

From `SnapshotService._build_league_state()` — the payload JSON structure stored in `league_snapshots.payload_json` is:

```json
{
  "league_id": "...",
  "trigger_context": { "triggered_by": "ingest" | "manual", ... },
  "state": {
    "league_name": "...",
    "season": "...",
    "rosters": [
      {
        "roster_id": 1,
        "owner_id": "...",
        "starters": [...],
        "players": [...],
        "reserve": [...],
        "taxi": [...],
        "standing": { "wins": 5, "losses": 3, ... },
        "direction": { "label": "True Contender", "confidence": 0.82 },
        "primary_weakness": "...",
        "player_values": [
          { "player_id": "...", "player_name": "...", "position": "...",
            "lens_market": 72.4, "lens_direction": 68.1, "lens_team_fit": 74.0,
            "comp_short_term": 65.0, "comp_age_curve": 55.0 }
        ]
      }
    ],
    "traded_picks": [...]
  },
  "delta": { "changed_players": [...], "changed_rosters": [...] }
}
```

**Gap:** `capital_score` is not stored in this payload. Phase 9 must add it. This is the primary modification to `SnapshotService`.

### TanStack Query hooks pattern

```typescript
// Four new query option objects following existing patterns in queries.ts

// staleTime: 5 * 60 * 1000 (5 min)
export const portfolioExposureOptions = () =>
  queryOptions({ queryKey: ['portfolio', 'exposure'], queryFn: ... })

// staleTime: 60 * 60 * 1000 (1 hour)
export const portfolioHealthOptions = () =>
  queryOptions({ queryKey: ['portfolio', 'health'], queryFn: ... })

// staleTime: 60 * 1000 (1 min)
export const snapshotAnchorsOptions = (leagueId: string) =>
  queryOptions({ queryKey: ['snapshot-anchors', leagueId], queryFn: ... })

// staleTime: 5 * 60 * 1000 (5 min)
export const snapshotDiffOptions = (leagueId: string, anchorId: number) =>
  queryOptions({ queryKey: ['snapshot-diff', leagueId, anchorId], queryFn: ... })
```

Stale times confirmed against 09-UI-SPEC.md. Confidence: HIGH.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cross-league player matrix | Custom array merge logic | DuckDB query with JSON_EXTRACT across rosters rows | DuckDB handles JSON field parsing natively; a Python loop is slower and unnecessary |
| Snapshot state reconstruction | Custom Python state rebuilder | Read existing `payload_json` from `league_snapshots` | The state is already serialized by `SnapshotService` — parse the JSON, don't re-query 5 tables |
| Anchor label formatting | Client-side date formatting | Backend provides verbatim label strings | UI-SPEC is explicit: frontend renders without transformation |
| Diff row sorting | Server-side sort param | Client-side sort by abs(delta) descending | Backend returns flat array; sort is trivial client-side, avoids query complexity |
| Portfolio route | shadcn Table | Custom HTML `<table>` with Tailwind | UI-SPEC is explicit: ExposureMatrix uses plain `<table>`, not shadcn Table |
| Retrospective grading scheduler | Celery / cron / background task | Manual CLI trigger or admin endpoint | D-13: runs once post-season on manual invocation |

---

## Common Pitfalls

### Pitfall 1: Confusing snapshot diff with snapshot rewrite
The snapshot comparison does NOT re-query live tables for the historical state. It reads the `payload_json` from `league_snapshots` for the chosen anchor. Only the current state comes from live tables. A common mistake is building a diff engine that queries historical tables — the historical data is already in the snapshot blob.

### Pitfall 2: Missing capital_score in snapshot payload
The current `SnapshotService` does not store `capital_score`. If Phase 9 plans a task to "read capital score from snapshot payload" without first planning a task to "add capital score to snapshot payload," the diff engine will have no data to diff against for pick capital. The snapshot service patch must come before the diff engine implementation.

### Pitfall 3: Treating prospect_model_outputs as always present
`prospect_model_outputs` is created by Phase 8. It may be empty or absent during development. PORT-06 grading must guard against this gracefully — return an empty grades result, not a 500 error.

### Pitfall 4: Portfolio page confusing "player exposure" with "player value"
The exposure matrix is about cross-league ownership presence — binary (owned / not owned). It does not re-display player values. Player values are the domain of the league drill-in. A player appearing on 3 rosters has "3-league concentration," not "high value." Do not conflate.

### Pitfall 5: Snapshot anchor list including every snapshot
The anchor list must be a filtered subset of `league_snapshots` — only snapshots tagged as event-anchored. A raw `SELECT * FROM league_snapshots ORDER BY snapshot_at` would return delta snapshots from every ingest run (potentially dozens), which are not meaningful anchors. The anchor detection query must filter to trade events and roster-change events using the threshold constant.

### Pitfall 6: Correlated risk detection scanning all players instead of cross-league overlap
Correlated NFL team risk is only meaningful when the same NFL team appears in 2+ connected leagues for the user. A player on one roster from the 49ers is not a correlation risk — two 49ers players across two different leagues is. The query must group by `(player.team, league_id)` pairs, not just by `player.team`.

### Pitfall 7: nav link in __root.tsx uses wrong TanStack Router active state
The existing nav uses `className="hover:text-foreground"` without active state styling on most links. The UI-SPEC specifies `data-[active=true]:text-primary` for active state on the Portfolio link. TanStack Router's `<Link>` component provides `data-status` and `activeProps`/`activeOptions` — use `activeProps={{ className: "text-primary" }}` or `data-[active=true]:text-primary`. Consistent with UI-SPEC note.

### Pitfall 8: Sheet panel navigation conflict in league drill-in
The Sheet panel for snapshot comparison uses the existing shadcn Sheet from Phase 5. Phase 5's Sheet is used for reroute paths in the trade evaluator. They share a component but are in different routes, so no conflict — but the developer must not re-initialize shadcn or install Sheet again. It is already installed.

---

## Plan Decomposition Guidance

Phase 9 has clear seams for plan breakdown. Five plans are recommended:

**Plan 09-01 — Backend foundation: portfolio package scaffold**
- `portfolio/` package with `constants.py`, `models.py`, `portfolio_repo.py`
- Alembic migration 007: `retrospective_runs` table
- PortfolioRepo: cross-league exposure query (reads `rosters` + `players`), correlated risk query
- Patch `SnapshotService._build_league_state()` to include `capital_score` per roster
- Unit tests for exposure computation and correlated cluster detection
- No router yet

**Plan 09-02 — Backend: snapshot diff engine + anchors**
- `snapshot_diff_engine.py`: anchor detection query (trade events + roster change events + season checkpoints), anchor label formatting, delta-forward diff computation
- `snapshot_diff.py` router: `GET /leagues/{league_id}/snapshot-anchors`, `GET /leagues/{league_id}/snapshot-diff`
- Register router in `main.py`
- Unit tests for anchor detection and diff field computation
- Integration test: verify diff against a seeded snapshot

**Plan 09-03 — Backend: retrospective grading engine + portfolio router**
- `retro_engine.py`: direction label grading (PORT-05), prospect tier grading (PORT-06), `retrospective_runs` write
- `portfolio_engine.py`: hedge recommendation string generation
- `portfolio.py` router: `GET /portfolio/exposure`, `GET /portfolio/health`
- Register router in `main.py`
- Unit tests for grading logic with mocked outcome data

**Plan 09-04 — Frontend: Portfolio page**
- `src/routes/portfolio.tsx`
- `ExposureMatrix` component (HTML table, not shadcn Table)
- `CorrelatedRiskSection` component
- Portfolio page footer with health indicator
- TanStack Query hooks for exposure and health
- Nav link in `__root.tsx`
- All four loading/empty/error states per UI-SPEC

**Plan 09-05 — Frontend: Snapshot comparison panel + human-verify checkpoint**
- `SnapshotComparisonSheet` component (existing Sheet)
- `AnchorSelector` component (existing Select)
- `SnapshotDiffView` component (diff rows with direction colors)
- "Compare to snapshot" button added to league drill-in header
- TanStack Query hooks for anchors and diff
- All loading/empty/error states per UI-SPEC
- Human-verify checkpoint: smoke test all four user-facing features (exposure matrix, correlated risk, snapshot diff, health indicator)

---

## Code Examples

### DuckDB cross-league exposure query

```python
# portfolio_repo.py — cross-league player ownership matrix
def load_exposure_rows(self) -> list[dict]:
    rows = self.conn.execute(
        """
        WITH roster_players AS (
            SELECT
                r.league_id,
                r.roster_id,
                UNNEST(FROM_JSON(r.players, '["VARCHAR"]')) AS player_id
            FROM rosters r
        ),
        player_leagues AS (
            SELECT
                rp.player_id,
                p.full_name,
                p.position,
                p.team,
                LIST(DISTINCT rp.league_id) AS owned_in_leagues,
                COUNT(DISTINCT rp.league_id) AS league_count
            FROM roster_players rp
            LEFT JOIN players p ON p.player_id = rp.player_id
            GROUP BY rp.player_id, p.full_name, p.position, p.team
        )
        SELECT player_id, full_name, position, team, owned_in_leagues, league_count
        FROM player_leagues
        ORDER BY league_count DESC, full_name
        """
    ).fetchall()
    return rows
```

Note: DuckDB's `UNNEST` with `FROM_JSON` is the correct pattern for JSON array columns. The `players` column in the `rosters` table is a JSON-serialized list of player_id strings. Confidence: HIGH (verified from existing `SnapshotService._build_league_state()` which uses `_loads(row[3], [])` to parse the same field).

### Snapshot anchor detection query

```python
# snapshot_diff_engine.py — anchor list for a league
def load_anchors(self, league_id: str) -> list[SnapshotAnchor]:
    # Trade-based anchors: snapshots taken immediately after a trade transaction
    trade_rows = self.conn.execute(
        """
        SELECT ls.id, ls.snapshot_at, t.created_at AS event_at
        FROM league_snapshots ls
        JOIN transactions t
          ON t.league_id = ls.league_id
          AND t.type = 'trade'
          AND t.status = 'complete'
          AND ABS(EPOCH(ls.snapshot_at) - EPOCH(t.created_at)) < 3600
        WHERE ls.league_id = ?
        ORDER BY ls.snapshot_at DESC
        """,
        [league_id],
    ).fetchall()

    # Roster-change anchors: snapshots where delta.changed_rosters >= threshold
    # These are identified by parsing payload_json.delta.changed_rosters length
    # (stored by SnapshotService when snapshot_type = 'delta')

    # Season checkpoint anchors: first and last snapshot per season
    checkpoint_rows = self.conn.execute(
        """
        SELECT id, snapshot_at, 'season_checkpoint' AS anchor_type
        FROM league_snapshots
        WHERE league_id = ?
          AND snapshot_type = 'full'
        ORDER BY snapshot_at
        """,
        [league_id],
    ).fetchall()
    ...
```

### SnapshotService capital_score extension

```python
# snapshot_service.py — add to _build_league_state() output
# After computing existing scorecard/direction/player_value data:
capital_scores: dict[int, float] = {}
try:
    from fantasy.picks.pick_engine import PickEngine  # Phase 6
    pick_engine = PickEngine(self.conn)
    for roster_id in [r["roster_id"] for r in rosters_data]:
        capital_scores[roster_id] = pick_engine.compute_capital_score(
            league_id=league_id,
            roster_id=roster_id,
        )
except ImportError:
    pass  # Phase 6 not available; capital score omitted from snapshot

# Then in each roster dict:
roster["capital_score"] = capital_scores.get(roster_id)
```

### Frontend: ExposureMatrix (HTML table, not shadcn Table)

```tsx
// ExposureMatrix.tsx — per UI-SPEC: custom HTML <table> with Tailwind
export function ExposureMatrix({ data, leagueNames }: ExposureMatrixProps) {
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-xs text-muted-foreground">
          <th className="text-left pb-2">Player</th>
          {leagueNames.map((name) => (
            <th key={name} className="text-center pb-2 max-w-[80px] truncate">
              {name.slice(0, 16)}
            </th>
          ))}
          <th className="text-left pb-2">Exposure</th>
        </tr>
      </thead>
      <tbody>
        {data.map((row, idx) => (
          <tr key={row.player_id} className={idx % 2 === 0 ? "bg-muted/30" : ""}>
            <td className="py-1 flex items-center gap-1">
              <span className="text-xs text-foreground">{row.full_name}</span>
              <Badge variant="outline" className="text-xs text-muted-foreground">
                {row.position}
              </Badge>
            </td>
            {leagueNames.map((name) => (
              <td key={name} className="text-center py-1">
                {row.owned_in_leagues.includes(name) && (
                  <Check size={14} className="text-green-700 dark:text-green-300 mx-auto" />
                )}
              </td>
            ))}
            <td className="py-1">
              <ConcentrationBadge count={row.league_count} />
              {row.league_count >= 3 && row.hedge_rec && (
                <p className="text-xs text-muted-foreground italic mt-0.5">
                  {row.hedge_rec}
                </p>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
```

### Frontend: SnapshotDiffView sort

```typescript
// Sort client-side: numeric deltas by abs magnitude desc,
// direction label changes after, departed players last
function sortDiffRows(rows: DiffRow[]): DiffRow[] {
  return [...rows].sort((a, b) => {
    if (a.type === "departed" && b.type !== "departed") return 1
    if (b.type === "departed" && a.type !== "departed") return -1
    if (a.type === "direction_label" && b.type !== "direction_label") return 1
    if (b.type === "direction_label" && a.type !== "direction_label") return -1
    return Math.abs(b.delta ?? 0) - Math.abs(a.delta ?? 0)
  })
}
```

---

## Confidence Summary

| Finding | Confidence | Source |
|---------|-----------|--------|
| No new npm/pip packages required | HIGH | Verified 09-UI-SPEC.md; all shadcn components already installed |
| `league_snapshots` table schema | HIGH | Verified from 005_league_snapshots.py migration |
| `team_directions`, `player_values`, `team_scorecards` schema | HIGH | Verified from 004_phase2_output_tables.py migration |
| SnapshotService does NOT store capital_score | HIGH | Verified by reading full snapshot_service.py |
| Portfolio package follows picks/ package structure | HIGH | Verified from 06-CONTEXT.md and existing trade/, profiling/ packages |
| ExposureMatrix uses plain HTML table | HIGH | Verified from 09-UI-SPEC.md implementation note 2 |
| Sheet component already installed (Phase 5) | HIGH | Verified from 09-UI-SPEC.md design system table |
| DuckDB UNNEST + FROM_JSON for players JSON field | HIGH | Consistent with SnapshotService JSON parsing pattern |
| Migration numbers: 007 for portfolio, 008 for Phase 8 | HIGH | Verified migration list: 001-006 exist |
| Next TanStack Router nav pattern | HIGH | Verified from __root.tsx |
| Retrospective grading must guard against absent prospect_model_outputs | HIGH | Phase 8 not yet executed; table may not exist |
| Phase 6 capital_score integration approach | MEDIUM | Phase 6 context read; exact PickEngine API not verified (plans not read) |

---

*Research complete: 2026-03-22*
*Phase: 09-portfolio-retrospectives*
