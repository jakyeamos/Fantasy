# Phase 3: Core Dashboard — Research

**Researched:** 2026-03-21
**Domain:** React 19 / Vite / TanStack Router + Query / shadcn/ui frontend scaffold; FastAPI dashboard and snapshot routers; DuckDB snapshot table design; post-ingest hook pattern
**Confidence:** HIGH (stack choices, project conventions, integration points); MEDIUM (snapshot delta DDL design — no single authoritative reference, but well-supported by DuckDB conventions)

---

## User Constraints

_Copied verbatim from 03-CONTEXT.md._

### Locked Decisions

| ID | Decision |
|----|----------|
| D-01 | League cards tile in a 2–3 column grid (user runs 3 leagues) |
| D-02 | Each card shows: league name, direction label, confidence band (High / Medium / Low — not a %, not a bar), primary team weakness with actionable nudge |
| D-03 | Direction label + confidence + primary weakness visible without scrolling — no collapsed sub-panels on card face |
| D-04 | Clicking a card drills into a league-specific view (separate route, not a modal or accordion) |
| D-05 | Risers/fallers time window is since last ingest run — not a fixed calendar window |
| D-06 | Show top 5 risers and top 5 fallers per league; same player appears once per league they're owned in — no deduplication |
| D-07 | Each riser/faller entry shows: player name, points delta (e.g., +8.2), reason string |
| D-08 | List filtered by actionability — players whose owners don't trade are excluded |
| D-09 | Phase 3 uses a placeholder heuristic for tradeability (recent transaction activity); Phase 4 manager data replaces this |
| D-10 | Main dashboard shows the single top exploit window per league on the league card |
| D-11 | Full exploit window list lives inside the league drill-in view |
| D-12 | Within drill-in, triggers grouped by league, collapsed per manager with expand to see individual triggers |
| D-13 | Each trigger includes a suggested action — not observation-only |
| D-14 | Multiple simultaneous triggers per manager collapse into one "high opportunity" signal; expand reveals all |
| D-15 | Snapshots triggered automatically after every successful ingest run — no separate scheduler |
| D-16 | Ingest-triggered snapshots are delta-only; once per calendar month a full snapshot is taken |
| D-17 | Manual "snapshot now" trigger available on main dashboard and inside each league's drill-in view |
| D-18 | Main dashboard shows last snapshot timestamp per league |
| D-19 | Snapshots are always full-portfolio — all connected leagues snapshotted together |

### Claude's Discretion

- Visual design of the league card (spacing, typography, shadow treatment)
- Exact routing structure (e.g., `/dashboard` → `/league/:id`)
- Loading and error states for each dashboard section
- Snapshot delta format (which fields are stored as diff vs. full copy)
- Specific heuristic used for Phase 3 tradeability placeholder

### Deferred Ideas (Out of Scope for Phase 3)

- Full behavioral tradeability filter for risers/fallers — requires Phase 4 manager trade history
- Historical snapshot comparison (side-by-side team state across time) — Phase 9 (PORT-02)
- Cross-league portfolio exposure dashboard (PORT-03, PORT-04) — Phase 9
- Top 3 quick-links per team on the main card (DASH-V2-01) — v2 backlog

---

## Summary

Phase 3 has two distinct halves:

**Backend half:** Two new FastAPI routers (`/dashboard` and `/snapshots`) and one Alembic migration (005) that creates the `league_snapshots` table. The dashboard router queries existing Phase 1 and Phase 2 tables — it does not compute anything itself. The snapshot service writes full or delta snapshots after every successful ingest and on manual trigger. The post-ingest hook is a single callback registered inside `IngestService.run()` just before it returns.

**Frontend half:** A greenfield React 19 / Vite / TanStack Router + Query / shadcn/ui app in a new `frontend/` directory. The main dashboard (`/`) shows league cards in a grid. Clicking a card navigates to `/league/$leagueId`. Both views are data-fetched via TanStack Query hitting the FastAPI backend.

No computation logic belongs in Phase 3. The direction label, confidence, player values, and scorecard sub-scores come from Phase 2 tables via query. Phase 3 only fetches, displays, and saves snapshots.

---

## Standard Stack

### Core — Frontend (new installs for Phase 3)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| react | 19.2.4 | UI framework | Project decision locked in roadmap |
| react-dom | 19.2.4 | DOM renderer | Paired with react |
| vite | 8.0.1 | Build tool | Project decision; fast HMR and tree-shaking |
| @tanstack/react-router | 1.168.1 | Type-safe routing with file-based routes | Project decision; full TypeScript path inference, pairs with TanStack Query |
| @tanstack/router-plugin | 1.167.2 | Vite plugin for file-based routing codegen | Required companion to TanStack Router for Vite |
| @tanstack/react-query | 5.91.3 | Server state, caching, background refetch | Project decision; standard v5 with queryOptions pattern |
| @tanstack/react-query-devtools | 5.x | Query inspection in dev | Required during development for cache visibility |
| tailwindcss | 4.2.2 | Utility CSS | Project decision; v4 CSS-first config |
| @tailwindcss/vite | 4.x | Tailwind v4 Vite plugin | Required for Tailwind v4 — replaces PostCSS approach |
| shadcn/ui (CLI) | latest | Copy-paste component library | Project decision; Card, Badge, Button components used on dashboard |
| tw-animate-css | latest | CSS animations for shadcn | Tailwind v4 replacement for deprecated `tailwindcss-animate` |
| typescript | 5.x | Type safety | Project decision |

### Core — Backend (new installs for Phase 3)

No new Python packages required. The full backend stack (FastAPI, DuckDB 1.5.0, Pydantic v2, Polars, Alembic) is already installed from Phase 1/2.

### Supporting — Frontend

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @tanstack/react-query-devtools | 5.x | Visual cache inspector | Dev only; wrap with `import.meta.env.DEV` guard |
| clsx | latest | Conditional className merging | Used inside shadcn/ui components; already installed by shadcn init |
| tailwind-merge | latest | Merge Tailwind classes without conflicts | Used by shadcn/ui `cn()` util |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| TanStack Router | React Router v7 | React Router is more mature but lacks TanStack Router's full type inference for params and search; project decision already locked |
| TanStack Router | React Router v7 | n/a — decision locked |
| shadcn/ui + Tailwind | MUI / Chakra | shadcn/ui is copy-paste (no runtime dep), integrates with Tailwind v4; decision locked |
| Tailwind v4 | Tailwind v3 | v4 CSS-first config — new projects should use v4; shadcn/ui now targets v4 by default |

**Installation:**
```bash
# Frontend scaffold (run from project root)
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install react@19.2.4 react-dom@19.2.4
npm install @tanstack/react-router@1.168.1 @tanstack/router-plugin@1.167.2
npm install @tanstack/react-query@5.91.3 @tanstack/react-query-devtools@5
npm install -D tailwindcss@4.2.2 @tailwindcss/vite typescript
npx shadcn@latest init -t vite
npx shadcn@latest add card badge button separator skeleton
```

**Version verification (confirmed 2026-03-21):**
- `vite`: 8.0.1 (npm registry)
- `react`: 19.2.4 (npm registry)
- `tailwindcss`: 4.2.2 (npm registry)
- `@tanstack/react-query`: 5.91.3 (npm registry)
- `@tanstack/react-router`: 1.168.1 (npm registry)
- `@tanstack/router-plugin`: 1.167.2 (npm registry)

---

## Architecture Patterns

### Recommended Project Structure

```
frontend/
├── src/
│   ├── routes/                     # TanStack Router file-based routes
│   │   ├── __root.tsx              # Root layout (QueryClientProvider, RouterDevtools)
│   │   ├── index.tsx               # Dashboard route — league card grid
│   │   └── league.$leagueId.tsx    # Drill-in route — per-league detail
│   ├── components/
│   │   ├── ui/                     # shadcn/ui generated components (Card, Badge, etc.)
│   │   ├── LeagueCard.tsx          # Main dashboard card (direction label, confidence, weakness)
│   │   ├── RisersFallersList.tsx   # Top 5 risers + 5 fallers table
│   │   ├── ExploitWindowPanel.tsx  # Trigger grouped view (drill-in)
│   │   └── SnapshotStatus.tsx      # Last snapshot timestamp + manual trigger button
│   ├── api/
│   │   └── queries.ts              # All queryOptions() definitions (queryKey + queryFn)
│   ├── lib/
│   │   └── utils.ts                # shadcn cn() helper
│   ├── routeTree.gen.ts            # Auto-generated by TanStack Router Vite plugin (do not edit)
│   ├── main.tsx                    # RouterProvider + QueryClientProvider
│   └── index.css                  # Tailwind v4 CSS-first config + @import "tw-animate-css"
├── vite.config.ts                  # @tailwindcss/vite plugin + @tanstack/router-plugin/vite
├── tsconfig.json
└── package.json

backend/src/fantasy/
├── routers/
│   ├── dashboard.py                # NEW — GET /dashboard/summary, GET /dashboard/league/{id}
│   └── snapshots.py                # NEW — POST /snapshots/trigger, GET /snapshots/status
├── snapshots/
│   ├── __init__.py
│   ├── snapshot_service.py         # NEW — SnapshotService.take_snapshot(conn, run_id?)
│   └── models.py                   # NEW — Pydantic models: SnapshotRecord, SnapshotStatus
└── alembic/versions/
    └── 005_league_snapshots.py     # NEW — league_snapshots table DDL
```

### Pattern 1: TanStack Router File-Based Routing

**What:** Routes defined as files in `src/routes/`. The Vite plugin generates `routeTree.gen.ts` at build time. `$leagueId` in filename becomes a typed path param.

**When to use:** All page-level navigation in this app.

```typescript
// Source: https://tanstack.com/router/v1/docs/framework/react/installation/with-vite
// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { tanstackRouter } from '@tanstack/router-plugin/vite'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    tanstackRouter({ target: 'react', autoCodeSplitting: true }),
    react(),
    tailwindcss(),
  ],
})
```

```typescript
// src/routes/league.$leagueId.tsx — drill-in route
import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/league/$leagueId')({
  component: LeagueDrillIn,
})

function LeagueDrillIn() {
  const { leagueId } = Route.useParams()
  // ...
}
```

### Pattern 2: queryOptions — Shared Type-Safe Query Definitions

**What:** Define all API calls as `queryOptions()` objects in a single `api/queries.ts`. Use them in `useQuery`, `useSuspenseQuery`, and imperative `queryClient.prefetchQuery` with full type inference.

**When to use:** Every backend API call. Do not inline queryKey/queryFn in components.

```typescript
// Source: https://tanstack.com/query/v5/docs/react/guides/query-options
// src/api/queries.ts
import { queryOptions } from '@tanstack/react-query'

export const dashboardSummaryOptions = queryOptions({
  queryKey: ['dashboard', 'summary'],
  queryFn: async () => {
    const res = await fetch('/api/dashboard/summary')
    if (!res.ok) throw new Error('Dashboard fetch failed')
    return res.json() as Promise<DashboardSummary>
  },
  staleTime: 5 * 60 * 1000,  // 5 minutes — data doesn't change between ingests
})

export const leagueDetailOptions = (leagueId: string) => queryOptions({
  queryKey: ['league', leagueId],
  queryFn: async () => {
    const res = await fetch(`/api/dashboard/league/${leagueId}`)
    if (!res.ok) throw new Error(`League ${leagueId} fetch failed`)
    return res.json() as Promise<LeagueDetail>
  },
  staleTime: 5 * 60 * 1000,
})

export const snapshotStatusOptions = queryOptions({
  queryKey: ['snapshots', 'status'],
  queryFn: async () => {
    const res = await fetch('/api/snapshots/status')
    if (!res.ok) throw new Error('Snapshot status fetch failed')
    return res.json() as Promise<SnapshotStatus[]>
  },
  staleTime: 30 * 1000,  // 30s — status can change after ingest
})
```

### Pattern 3: shadcn/ui Card as League Card

**What:** Compose the Card primitive with Badge (direction label), text blocks (confidence band, weakness), and a Link for drill-in navigation.

**When to use:** Every league card in the main grid.

```typescript
// src/components/LeagueCard.tsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Link } from '@tanstack/react-router'

interface LeagueCardProps {
  leagueId: string
  leagueName: string
  directionLabel: string
  confidenceBand: 'High' | 'Medium' | 'Low'
  primaryWeakness: string
  topExploitWindow: string | null
  lastSnapshotAt: string | null
}

export function LeagueCard({ leagueId, leagueName, directionLabel, confidenceBand, primaryWeakness, topExploitWindow, lastSnapshotAt }: LeagueCardProps) {
  return (
    <Link to="/league/$leagueId" params={{ leagueId }}>
      <Card className="cursor-pointer hover:shadow-md transition-shadow h-full">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">{leagueName}</CardTitle>
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold">{directionLabel}</span>
            <Badge variant={confidenceBand === 'High' ? 'default' : confidenceBand === 'Medium' ? 'secondary' : 'outline'}>
              {confidenceBand}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-2">
          <p className="text-sm">{primaryWeakness}</p>
          {topExploitWindow && (
            <p className="text-xs text-muted-foreground border-t pt-2">{topExploitWindow}</p>
          )}
          {lastSnapshotAt && (
            <p className="text-xs text-muted-foreground">Last snapshot: {lastSnapshotAt}</p>
          )}
        </CardContent>
      </Card>
    </Link>
  )
}
```

### Pattern 4: FastAPI Dashboard Router — Read-Only Aggregation

**What:** The dashboard router assembles data from Phase 1 and Phase 2 tables via direct DuckDB queries. It does not call engine logic — engines run during ingest. The router only reads already-computed results.

**When to use:** `GET /dashboard/summary` (all leagues), `GET /dashboard/league/{league_id}` (drill-in).

```python
# backend/src/fantasy/routers/dashboard.py
from __future__ import annotations
from fastapi import APIRouter, Depends
import duckdb
from fantasy.routers.deps import get_read_db_conn

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/summary")
def get_dashboard_summary(conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn)):
    # Join leagues + team_directions + ingest_runs for card data
    rows = conn.execute("""
        SELECT
            l.league_id,
            l.name,
            td.primary_label,
            td.confidence,
            td.reasoning,
            ir.completed_at AS last_ingest_at,
            ls.snapshot_at AS last_snapshot_at
        FROM leagues l
        LEFT JOIN team_directions td
            ON l.league_id = td.league_id
            AND td.computed_at = (
                SELECT MAX(computed_at) FROM team_directions
                WHERE league_id = l.league_id
            )
        LEFT JOIN ingest_runs ir
            ON l.league_id = ir.league_id
            AND ir.status = 'complete'
            AND ir.completed_at = (
                SELECT MAX(completed_at) FROM ingest_runs
                WHERE league_id = l.league_id AND status = 'complete'
            )
        LEFT JOIN league_snapshots ls
            ON l.league_id = ls.league_id
            AND ls.snapshot_at = (
                SELECT MAX(snapshot_at) FROM league_snapshots
                WHERE league_id = l.league_id
            )
    """).fetchall()
    # ...shape into response dicts
```

### Pattern 5: Snapshot Table DDL and Service Design

**What:** `league_snapshots` stores a JSON blob of the team state at a point in time. Ingest-triggered snapshots are delta-only (only changed fields vs. previous snapshot); once-per-calendar-month snapshots are full. Both share the same table; `snapshot_type` distinguishes them.

**When to use:** Alembic migration 005.

```sql
-- Migration 005 DDL (DuckDB-compatible, op.execute() pattern)
CREATE TABLE IF NOT EXISTS league_snapshots (
    id              INTEGER PRIMARY KEY,
    league_id       VARCHAR NOT NULL,
    snapshot_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    snapshot_type   VARCHAR NOT NULL,          -- 'delta' | 'full'
    triggered_by    VARCHAR NOT NULL,           -- 'ingest' | 'manual'
    ingest_run_id   INTEGER,                    -- FK to ingest_runs.id (nullable for manual)
    payload_json    VARCHAR NOT NULL,           -- JSON blob: full or delta state
    base_snapshot_id INTEGER                    -- for delta: which snapshot this diffs against
)
```

The `SnapshotService` follows the same DuckDB connection + upsert pattern as `LeagueRepo`:

```python
# backend/src/fantasy/snapshots/snapshot_service.py
class SnapshotService:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn

    def take_snapshot(
        self,
        league_ids: list[str],
        triggered_by: str,
        ingest_run_id: int | None = None,
    ) -> list[int]:
        """
        Snapshot all leagues together (D-19).
        Decides delta vs full based on: whether a snapshot exists in current calendar month.
        Returns list of inserted snapshot IDs.
        """
        ...
```

### Pattern 6: Post-Ingest Hook in IngestService

**What:** After `IngestService.run()` marks the run complete (status = 'complete'), call `SnapshotService.take_snapshot()` before returning the run_id. This is a synchronous call — snapshot writes happen in the same DuckDB connection before the conn closes.

**When to use:** Replace the `return run_id` line in `IngestService.run()` with a snapshot call then return.

```python
# backend/src/fantasy/ingestion/ingest_service.py (modification point)
# After the UPDATE ingest_runs SET status = 'complete' block:

from fantasy.snapshots.snapshot_service import SnapshotService

snapshot_svc = SnapshotService(self.conn)
snapshot_svc.take_snapshot(
    league_ids=[league_id],  # SnapshotService internally fetches all leagues (D-19)
    triggered_by="ingest",
    ingest_run_id=run_id,
)
return run_id
```

**IMPORTANT:** D-19 says "all connected leagues snapshotted together." The snapshot service must query `SELECT league_id FROM leagues` to get all leagues, not just the one being ingested. The `league_ids` param in the hook call is used only to record which ingest triggered it.

### Pattern 7: Grid Layout — Responsive 2–3 Column

**What:** Tailwind CSS grid with `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` gives the 2–3 column layout across viewport sizes. For exactly 3 leagues (D-01), all 3 cards appear in a single row on desktop.

```typescript
// src/routes/index.tsx — dashboard grid
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 p-6">
  {leagues.map(league => (
    <LeagueCard key={league.leagueId} {...league} />
  ))}
</div>
```

### Anti-Patterns to Avoid

- **Computing direction labels in the dashboard router:** The router is read-only. Direction labels come from `team_directions` table (Phase 2 output). Never call engine logic from a dashboard endpoint.
- **Per-league snapshot triggers:** D-19 is explicit — snapshots are always full-portfolio. Do not build a per-league snapshot path.
- **Separate scheduler for snapshots:** D-15 is explicit — snapshot trigger is the post-ingest hook. Do not add APScheduler or any background scheduler to the backend.
- **Deduplicating risers/fallers across leagues:** D-06 is explicit — same player appears once per league they're owned in.
- **Modal or accordion drill-in:** D-04 is explicit — drill-in is a separate route (`/league/:id`), not a modal.
- **Using tailwindcss-animate:** It is deprecated in Tailwind v4. Use `tw-animate-css` instead.
- **Editing routeTree.gen.ts:** This file is auto-generated by the TanStack Router Vite plugin. Never edit manually.
- **Inline queryKey/queryFn in components:** Define all queries in `src/api/queries.ts` using `queryOptions()`. This enables type-safe prefetching and cache inspection.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Routing with typed params | Custom router context | TanStack Router file-based routing | `$leagueId` param is automatically typed; navigation is type-checked at compile time |
| Server state caching | Custom fetch + useState | TanStack Query `useQuery` + `queryOptions` | Handles stale-while-revalidate, background refetch, error/loading states, cache invalidation |
| Card, Badge, Button UI | Custom CSS components | shadcn/ui primitives | Accessible, Radix-based, Tailwind-compatible; copy-paste means zero runtime dep |
| Conditional className merging | String template literals | `cn()` from shadcn + `clsx` + `tailwind-merge` | Prevents Tailwind class conflicts (e.g., `bg-red-500 bg-blue-500`) |
| Snapshot delta computation | Custom diff algorithm | JSON serialization of changed fields vs. full blob | At this data scale (3 leagues, ~20 players per roster), full JSON blobs are cheap; delta means "store fields that changed since last snapshot," not a structural diff |
| Snapshot scheduling | APScheduler / cron | Post-ingest hook in `IngestService.run()` | D-15 explicitly prohibits a separate scheduler; hook is simpler, guaranteed to run, tied to successful ingest |

**Key insight:** The dashboard is a read-only view over Phase 2 computed data. All complexity lives in the computation phase. Phase 3 adds exactly: (a) read endpoints that join existing tables, and (b) a snapshot write that fires post-ingest. This is the right scope.

---

## Common Pitfalls

### 1. Tailwind v4 CSS-First Config (HIGH risk)
Tailwind v4 removes `tailwind.config.js`. All config lives in `src/index.css` using `@theme` blocks. If you generate a `tailwind.config.js`, it will be silently ignored. Use `@tailwindcss/vite` in `vite.config.ts` (not PostCSS).

**Prevention:** Confirm `vite.config.ts` uses `import tailwindcss from '@tailwindcss/vite'` and includes it in `plugins`. No `postcss.config.js` needed.

### 2. shadcn/ui Requires Path Aliases
`shadcn/ui init` configures `@/` path alias in `tsconfig.json` and `vite.config.ts`. If the alias is missing, all component imports break silently.

**Prevention:** Run `npx shadcn@latest init -t vite` before adding any components. Verify `tsconfig.json` has `"paths": { "@/*": ["./src/*"] }` and `vite.config.ts` has the corresponding `resolve.alias`.

### 3. TanStack Router Plugin Must Load Before React Plugin
The order of plugins in `vite.config.ts` matters. `tanstackRouter` must appear before `react()` in the plugins array.

**Prevention:** Always order plugins as: `[tanstackRouter(...), react(), tailwindcss()]`.

### 4. routeTree.gen.ts Is Not Committed Initially
The file is generated on first `vite dev` or `vite build`. Tests or CI that run before a dev server has been started will fail to find the file.

**Prevention:** Add `vite build` (or `tsc --noEmit`) as the first step in any CI that needs the route tree. Or pre-generate it with `npx @tanstack/router-cli generate`.

### 5. DuckDB Read/Write Connection Conflict
DuckDB 1.5.0 only allows one write connection at a time. The snapshot write inside `IngestService.run()` already holds the write connection. The snapshot service must use the same connection passed into `IngestService`, not open a new one.

**Prevention:** Pass `self.conn` (the IngestService's write connection) into `SnapshotService`. Do not call `get_write_connection()` inside SnapshotService when invoked from an ingest context.

### 6. Snapshot Post-Ingest Hook Must Fire After status='complete' Write
If `take_snapshot()` is called before `UPDATE ingest_runs SET status = 'complete'`, a crash during snapshot will leave the run in a `running` state permanently.

**Prevention:** The snapshot call must appear after the `UPDATE ingest_runs SET status = 'complete'` execute block and before `return run_id`.

### 7. Alembic Migration 005 Revision Chain
The migration chain is `001 → 002 → 003`. Phase 2 adds `004`. Phase 3 must use `down_revision = "004_phase2_output_tables"` (matching the exact revision string used in migration 004). Using the wrong string causes `alembic upgrade head` to fail with a revision-not-found error.

**Prevention:** Before writing migration 005, run `ls backend/alembic/versions/` to confirm the exact 004 revision filename and check its `revision` field.

### 8. Risers/Fallers "Since Last Ingest" Window
The time window for risers/fallers is `completed_at` of the most recent complete `ingest_run` for that league (D-05). This requires a correlated subquery or JOIN against `ingest_runs`. Using `CURRENT_TIMESTAMP - INTERVAL 24 HOURS` is wrong — it doesn't match the decision.

**Prevention:** The dashboard endpoint must join `ingest_runs WHERE status = 'complete' ORDER BY completed_at DESC LIMIT 1` to get the cursor timestamp.

### 9. Confidence Band is Text, Not a Number
D-02 specifies the confidence band as "High / Medium / Low" — not a percentage, not a progress bar. The `team_directions` table stores a float `confidence` score (0.0–1.0). The dashboard router converts it to a band label server-side before returning JSON.

**Suggested thresholds (Claude's discretion):**
- `confidence >= 0.70` → "High"
- `confidence >= 0.45` → "Medium"
- `confidence < 0.45` → "Low"

**Prevention:** Never pass the raw float to the frontend. Convert to band in the FastAPI response model.

### 10. Phase 2 Tables May Not Exist Yet (Graceful Degradation)
At Phase 3 development time, Phase 2 engines may not be fully implemented. The dashboard router must handle `NULL` rows from `team_directions` and `player_values` gracefully (return a placeholder card state) rather than raising a 500.

**Prevention:** Use `LEFT JOIN` for all Phase 2 table joins. Return `direction_label: "Pending"` and empty arrays when Phase 2 data is absent.

---

## Code Examples

### Vite Config (complete)
```typescript
// frontend/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { tanstackRouter } from '@tanstack/router-plugin/vite'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig({
  plugins: [
    tanstackRouter({ target: 'react', autoCodeSplitting: true }),
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8000',  // FastAPI backend
    },
  },
})
```

### Root Layout with Providers
```typescript
// frontend/src/routes/__root.tsx
import { createRootRoute, Outlet } from '@tanstack/react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 5 * 60 * 1000 },
  },
})

export const Route = createRootRoute({
  component: () => (
    <QueryClientProvider client={queryClient}>
      <Outlet />
      {import.meta.env.DEV && <ReactQueryDevtools />}
    </QueryClientProvider>
  ),
})
```

### Manual Snapshot Trigger (mutation pattern)
```typescript
// src/components/SnapshotStatus.tsx
import { useMutation, useQueryClient } from '@tanstack/react-query'

function triggerSnapshot() {
  return fetch('/api/snapshots/trigger', { method: 'POST' }).then(r => {
    if (!r.ok) throw new Error('Snapshot trigger failed')
    return r.json()
  })
}

export function SnapshotStatus({ lastSnapshotAt }: { lastSnapshotAt: string | null }) {
  const queryClient = useQueryClient()
  const { mutate, isPending } = useMutation({
    mutationFn: triggerSnapshot,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['snapshots', 'status'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'summary'] })
    },
  })

  return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground">
      {lastSnapshotAt ? `Last snapshot: ${lastSnapshotAt}` : 'No snapshot yet'}
      <button
        onClick={() => mutate()}
        disabled={isPending}
        className="underline hover:no-underline disabled:opacity-50"
      >
        {isPending ? 'Saving...' : 'Snapshot now'}
      </button>
    </div>
  )
}
```

### Snapshot Router (backend)
```python
# backend/src/fantasy/routers/snapshots.py
from fastapi import APIRouter, Depends, BackgroundTasks
import duckdb
from fantasy.routers.deps import get_write_db_conn
from fantasy.snapshots.snapshot_service import SnapshotService

router = APIRouter(prefix="/snapshots", tags=["snapshots"])

@router.post("/trigger")
def trigger_snapshot(conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn)):
    """Manual snapshot trigger — snapshots all connected leagues."""
    league_ids = [row[0] for row in conn.execute("SELECT league_id FROM leagues").fetchall()]
    svc = SnapshotService(conn)
    snapshot_ids = svc.take_snapshot(
        league_ids=league_ids,
        triggered_by="manual",
        ingest_run_id=None,
    )
    return {"snapshot_ids": snapshot_ids, "count": len(snapshot_ids)}

@router.get("/status")
def get_snapshot_status(conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn)):
    """Return last snapshot timestamp per league."""
    rows = conn.execute("""
        SELECT league_id, MAX(snapshot_at) as last_snapshot_at
        FROM league_snapshots
        GROUP BY league_id
    """).fetchall()
    return [{"league_id": r[0], "last_snapshot_at": str(r[1])} for r in rows]
```

---

## Integration Notes

### Phase 2 Table Dependency
The dashboard reads `team_directions` and `team_scorecards` (Phase 2 output tables). These tables exist after Alembic migration 004 runs. They will be empty until Phase 2 engines execute. The dashboard router must handle empty/NULL gracefully (see Pitfall 10).

**Fields consumed from Phase 2:**
- `team_directions`: `league_id`, `roster_id`, `primary_label`, `confidence`, `reasoning`, `approved_moves`, `discouraged_moves`, `computed_at`
- `team_scorecards`: `league_id`, `roster_id`, `composite`, all 9 sub-scores — used to derive "primary team weakness" as the sub-score with the lowest value
- `player_values`: `league_id`, `roster_id`, `player_id`, `lens_production`, `lens_market`, `computed_at` — used for risers/fallers delta

**Primary weakness derivation:** Query `team_scorecards` for the user's team (by `owner_id` match via `rosters`), find the sub-score with the minimum value. Map sub-score name to human-readable weakness string with actionable nudge.

### IngestService Modification Scope
Phase 3 modifies exactly one file in the existing backend: `backend/src/fantasy/ingestion/ingest_service.py`. The modification is the snapshot hook at the end of the `run()` method's success path. No other existing files change.

### Alembic Migration Sequence
```
001_initial_schema
002_add_player_stats_weekly
003_add_adp_baseline
004_phase2_output_tables      ← Phase 2 (creates team_scorecards, team_directions, player_values)
005_league_snapshots          ← Phase 3 (creates league_snapshots)
```

Migration 005 revision string: `"005_league_snapshots"`, `down_revision = "004_phase2_output_tables"`.

---

*Phase: 03-core-dashboard*
*Research completed: 2026-03-21*
*Sources verified: npm registry (2026-03-21), TanStack docs, shadcn/ui docs, existing codebase inspection*
