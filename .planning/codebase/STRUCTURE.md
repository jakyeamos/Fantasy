# Codebase Structure

**Analysis Date:** 2026-03-22

## Directory Layout

```
Fantasy/                          # Repo root
├── .env                          # Local env vars (FANTASY_* prefix)
├── .gitignore
├── .planning/                    # GSD planning documents and phase plans
│   ├── codebase/                 # Codebase map documents (this file lives here)
│   ├── phases/                   # Per-phase plan and summary files
│   └── research/                 # Research artifacts
├── data/
│   └── fantasy.duckdb            # Single-file embedded database
├── backend/
│   ├── alembic/                  # Database migration scripts
│   │   └── versions/             # Numbered migration files (001–010)
│   ├── src/fantasy/              # All Python application code
│   │   ├── main.py               # FastAPI app factory + lifespan
│   │   ├── config.py             # Pydantic settings (FANTASY_* env vars)
│   │   ├── startup_tasks.py      # Dev auto-refresh + schema compat logic
│   │   ├── db/                   # Database layer
│   │   │   ├── connection.py     # get_read_connection / get_write_connection
│   │   │   └── models.py         # SQLAlchemy Core table definitions
│   │   ├── routers/              # FastAPI route handlers (one file per domain)
│   │   │   ├── deps.py           # Shared DuckDB connection dependencies
│   │   │   ├── dashboard.py      # /dashboard/* — league summary and detail
│   │   │   ├── ingest.py         # /ingest/* — trigger and status
│   │   │   ├── intelligence.py   # /intelligence/* — scorecard/direction/value
│   │   │   ├── trade.py          # /trade/* — evaluate, search players/picks
│   │   │   ├── profiling.py      # /profiling/* — manager profiles
│   │   │   ├── picks.py          # /picks/* — pick valuation
│   │   │   ├── rookie_board.py   # /rookie-board/* — tiered rookie rankings
│   │   │   ├── draft_room.py     # /draft-room/* — on-the-clock advisor
│   │   │   ├── snapshots.py      # /snapshots/* — trigger and status
│   │   │   ├── corrections.py    # /corrections/* — manual data overrides
│   │   │   └── health.py         # /health — liveness check
│   │   ├── ingestion/            # Sleeper API ingestion domain
│   │   │   ├── ingest_service.py # Orchestrates full/incremental ingest
│   │   │   ├── sleeper_client.py # Async httpx client for Sleeper API
│   │   │   ├── sleeper_mapper.py # Raw API → typed dataclasses
│   │   │   ├── nfl_data_loader.py# Loads ADP baseline CSV into DB
│   │   │   └── gap_detector.py   # Detects missing transaction weeks
│   │   ├── intelligence/         # Team scoring and direction domain
│   │   │   ├── models.py         # TeamScorecard, DirectionResult, PlayerValue
│   │   │   ├── constants.py      # Direction labels, scoring weights
│   │   │   ├── intelligence_service.py  # Orchestrates scorecard→direction→value
│   │   │   ├── scorecard_engine.py      # 9-dimension roster scoring
│   │   │   ├── direction_engine.py      # Classifies scorecard into direction
│   │   │   └── valuation_engine.py      # Per-player direction-aware values
│   │   ├── trade/                # Trade evaluation domain
│   │   │   ├── models.py         # TradeAsset, TradeRequest, TradeEvaluation, etc.
│   │   │   ├── constants.py      # Thresholds and pick market values
│   │   │   ├── trade_engine.py   # 7-dimension trade scoring
│   │   │   ├── trade_repo.py     # SQL for players, picks, scorecards, values
│   │   │   ├── package_builder.py# Builds aggressive/fair package offers
│   │   │   └── reroute_engine.py # Suggests better targets or packages
│   │   ├── profiling/            # Manager behavior profiling domain
│   │   │   ├── models.py         # ManagerProfile, PitchAngle, etc.
│   │   │   ├── constants.py      # Exploitation type labels and weights
│   │   │   ├── profiling_engine.py  # Computes manager exploit profile
│   │   │   └── profiling_repo.py    # SQL for profile storage/retrieval
│   │   ├── picks/                # Dynamic pick valuation domain
│   │   │   ├── models.py         # PickValue
│   │   │   ├── constants.py      # Valuation weights
│   │   │   ├── pick_engine.py    # Computes base/timed/adjusted pick values
│   │   │   └── pick_repo.py      # SQL for traded picks and pick_values table
│   │   ├── rookie/               # Rookie board and draft room domain
│   │   │   ├── models.py         # RookieBoardResult, DraftRoomResult
│   │   │   ├── constants.py      # Tier thresholds, archetype labels
│   │   │   ├── rookie_engine.py  # Computes tiered board and draft advice
│   │   │   └── rookie_repo.py    # SQL for ADP, stats, and board output
│   │   ├── snapshots/            # Point-in-time roster snapshot domain
│   │   │   └── snapshot_service.py
│   │   ├── repositories/         # Cross-domain shared repo
│   │   │   └── league_repo.py    # Upserts leagues, rosters, standings, picks, transactions
│   │   └── corrections/          # Manual data override domain
│   │       └── override_service.py
│   └── tests/                    # Pytest test suite (mirrors src structure)
│       ├── conftest.py
│       ├── integration/          # Integration tests (full router stack)
│       ├── intelligence/         # Intelligence engine unit tests
│       ├── picks/                # Pick engine and repo unit tests
│       ├── rookie/               # Rookie engine unit tests
│       └── test_*.py             # Domain-level unit tests
└── frontend/
    ├── src/
    │   ├── main.tsx              # App entry: QueryClient + RouterProvider
    │   ├── routeTree.gen.ts      # Auto-generated by TanStack Router
    │   ├── index.css             # Tailwind base + CSS variable theme tokens
    │   ├── api/
    │   │   ├── queries.ts        # All TanStack Query queryOptions definitions
    │   │   └── types.ts          # All TypeScript API response interfaces
    │   ├── routes/               # File-based route components
    │   │   ├── __root.tsx        # Root layout with nav header and theme toggle
    │   │   ├── index.tsx         # / — dashboard summary (LeagueCard grid)
    │   │   ├── league.$leagueId.tsx              # /league/:id — league detail
    │   │   ├── league.$leagueId.managers.tsx     # /league/:id/managers — manager list
    │   │   ├── league.$leagueId.managers.$managerId.tsx  # Manager dossier
    │   │   ├── league.$leagueId.rookie-board.tsx # Rookie board
    │   │   ├── trades.tsx        # /trades — trade evaluator
    │   │   └── draft-room.tsx    # /draft-room — on-the-clock advisor
    │   ├── components/
    │   │   ├── ui/               # Primitive UI components (shadcn-style)
    │   │   │   ├── button.tsx
    │   │   │   ├── card.tsx
    │   │   │   ├── badge.tsx
    │   │   │   ├── skeleton.tsx
    │   │   │   └── separator.tsx
    │   │   ├── trade/            # Trade evaluator components
    │   │   │   ├── AssetChip.tsx
    │   │   │   ├── DimensionScoreRow.tsx
    │   │   │   ├── EvaluationOutputPanel.tsx
    │   │   │   ├── StrategicDistinctionBanner.tsx
    │   │   │   ├── PackageBuilderPanel.tsx
    │   │   │   └── RerouteSheet.tsx
    │   │   ├── picks/            # Pick valuation components
    │   │   │   ├── LeaguePickList.tsx
    │   │   │   ├── PickValueSummaryRow.tsx
    │   │   │   └── TimingBadge.tsx
    │   │   ├── rookie/           # Rookie board components
    │   │   │   ├── RookiePlayerCard.tsx
    │   │   │   ├── TierGroup.tsx
    │   │   │   └── TierDivider.tsx
    │   │   ├── draft-room/       # Draft room components
    │   │   │   ├── VerdictBanner.tsx
    │   │   │   └── TendencyWarningList.tsx
    │   │   ├── LeagueCard.tsx    # Dashboard summary card per league
    │   │   ├── ExploitWindowPanel.tsx
    │   │   ├── RisersFallersList.tsx
    │   │   ├── SnapshotStatus.tsx
    │   │   ├── ManagerListRow.tsx
    │   │   ├── DossierOverviewTab.tsx
    │   │   ├── DossierPitchAnglesTab.tsx
    │   │   └── DossierTradeHistoryTab.tsx
    │   └── lib/
    │       ├── utils.ts          # cn() helper, formatModelLabel
    │       └── theme.ts          # Dark/light theme helpers and constants
    └── dist/                     # Vite build output (not committed)
```

## Directory Purposes

**`backend/src/fantasy/routers/`:**
- Purpose: HTTP boundary — request parsing, response serialization, dependency injection
- Contains: One module per domain; each exports a `router = APIRouter(prefix=...)` imported by `main.py`
- Key files: `deps.py` for shared `Depends()` providers, `dashboard.py` (largest, ~1000 lines)

**`backend/src/fantasy/<domain>/`:**
- Purpose: Self-contained domain package with models, logic, and data access
- Pattern: Each domain has at minimum `models.py` + an `*_engine.py` or `*_service.py`; most also have `*_repo.py` and `constants.py`
- Key domains: `intelligence/`, `trade/`, `profiling/`, `picks/`, `rookie/`

**`backend/src/fantasy/db/`:**
- Purpose: Database schema definitions and connection management only
- Contains: `models.py` (SQLAlchemy Core table objects), `connection.py` (two factory functions)
- Note: No ORM — all SQL is hand-written in repo classes

**`backend/alembic/versions/`:**
- Purpose: Schema evolution; numbered sequentially 001–010
- Generated: No (hand-written)
- Committed: Yes

**`data/`:**
- Purpose: DuckDB database file at runtime, ADP baseline CSV (optional)
- Key file: `data/fantasy.duckdb` — the entire persistent store
- Generated: Yes (at runtime); `.duckdb` file is gitignored

**`frontend/src/api/`:**
- Purpose: All network communication and shared TypeScript types
- Key files: `queries.ts` (all `queryOptions` definitions), `types.ts` (all response interfaces)
- Note: No ad-hoc `fetch()` calls in route or component files — all go through `getJson<T>` in `queries.ts`

**`frontend/src/routes/`:**
- Purpose: Page-level components; each file maps to a URL segment via TanStack Router file conventions
- Naming: `league.$leagueId.tsx` → `/league/:leagueId` (dots separate segments, `$` marks params)

**`frontend/src/components/ui/`:**
- Purpose: Unstyled primitive components (shadcn-style pattern); wrapped by feature components
- Contains: `button.tsx`, `card.tsx`, `badge.tsx`, `skeleton.tsx`, `separator.tsx`
- Generated: No (manually maintained)

## Key File Locations

**Entry Points:**
- `backend/src/fantasy/main.py`: FastAPI app factory; registers all routers
- `frontend/src/main.tsx`: React app bootstrap with QueryClient and RouterProvider

**Configuration:**
- `backend/src/fantasy/config.py`: All settings via `Settings(BaseSettings)` with `FANTASY_` prefix
- `.env`: Root-level env file consumed by `config.py`

**Core Logic:**
- `backend/src/fantasy/intelligence/scorecard_engine.py`: 9-dimension roster scoring
- `backend/src/fantasy/trade/trade_engine.py`: 7-dimension trade evaluation
- `backend/src/fantasy/picks/pick_engine.py`: Dynamic pick valuation
- `backend/src/fantasy/rookie/rookie_engine.py`: Tiered rookie board + draft room

**Data Schema:**
- `backend/src/fantasy/db/models.py`: All table definitions (SQLAlchemy Core)
- `backend/alembic/versions/`: Migration history

**API Contract (frontend ↔ backend):**
- `frontend/src/api/types.ts`: TypeScript interfaces matching all Pydantic response models
- `frontend/src/api/queries.ts`: All TanStack Query options with typed `queryFn`

**Testing:**
- `backend/tests/conftest.py`: Shared fixtures (in-memory DuckDB, test data factories)
- `backend/tests/integration/`: Full-stack router tests
- `backend/tests/intelligence/`, `backend/tests/picks/`, `backend/tests/rookie/`: Domain-specific unit tests

## Naming Conventions

**Backend Files:**
- Domain packages: `snake_case/` directory matching the domain noun (e.g., `intelligence/`, `trade/`, `picks/`)
- Engine classes: `<Domain>Engine` (e.g., `ScorecardEngine`, `TradeEngine`, `PickEngine`)
- Service classes: `<Domain>Service` (e.g., `IngestService`, `IntelligenceService`, `SnapshotService`)
- Repo classes: `<Domain>Repo` (e.g., `LeagueRepo`, `TradeRepo`, `PickRepo`)
- Constants modules: `constants.py` within each domain
- Alembic migrations: `NNN_description.py` (e.g., `009_pick_values.py`)

**Frontend Files:**
- Route files: `segment.tsx` or `segment.$param.tsx` (TanStack Router convention)
- Feature components: `PascalCase.tsx` (e.g., `LeagueCard.tsx`, `DossierOverviewTab.tsx`)
- Domain component folders: `lowercase-kebab/` (e.g., `draft-room/`, `picks/`, `rookie/`, `trade/`)
- API types: interfaces in `PascalCase` (e.g., `TradeEvaluation`, `ManagerProfile`)
- Query options: `<scope>Options` functions (e.g., `leagueDetailOptions`, `pickValuesOptions`)

**Directories:**
- Backend domains: `snake_case` matching Python module names
- Frontend components: lowercase with hyphens for multi-word sub-folders

## Where to Add New Code

**New backend domain (e.g., `portfolio/`):**
- Create `backend/src/fantasy/portfolio/` with `__init__.py`, `models.py`, `constants.py`, `portfolio_engine.py`, `portfolio_repo.py`
- Add router at `backend/src/fantasy/routers/portfolio.py`
- Register router in `backend/src/fantasy/main.py`
- Add DB migration in `backend/alembic/versions/NNN_portfolio_tables.py`
- Add tests at `backend/tests/portfolio/` and `backend/tests/test_portfolio_router.py`

**New backend router endpoint:**
- Add to the appropriate `backend/src/fantasy/routers/<domain>.py`
- Use `Depends(get_read_db_conn)` for read-only endpoints, `Depends(get_write_db_conn)` for mutations
- Instantiate engine/repo inside the handler function (not at module level, except `OverrideService` which has no connection)

**New frontend route/page:**
- Create `frontend/src/routes/<segment>.tsx` following TanStack Router file naming
- `routeTree.gen.ts` is regenerated automatically by the dev server
- Fetch data with `useQuery(someOptions(params))` from `api/queries.ts`

**New frontend feature component:**
- Feature-scoped: add to `frontend/src/components/<domain>/`
- Shared across domains: add to `frontend/src/components/` (top level)
- UI primitives: add to `frontend/src/components/ui/`

**New TanStack Query definition:**
- Add `queryOptions(...)` to `frontend/src/api/queries.ts`
- Add matching TypeScript interface to `frontend/src/api/types.ts`

**New player/pick stat computation:**
- SQL reads go in the domain `*_repo.py`
- Computation logic goes in the domain `*_engine.py`
- Persist output via repo upsert methods; do not write SQL in engine classes

## Special Directories

**`.planning/`:**
- Purpose: GSD planning documents, phase plans, codebase maps
- Generated: No (hand-authored)
- Committed: Yes

**`data/`:**
- Purpose: Runtime database and optional ADP CSV
- Generated: Yes (`fantasy.duckdb` created at first server start)
- Committed: Partial — `adp_baseline.csv` may be committed; `fantasy.duckdb` is gitignored

**`frontend/dist/`:**
- Purpose: Vite production build output
- Generated: Yes
- Committed: No

**`backend/.venv/`:**
- Purpose: Python virtual environment
- Generated: Yes
- Committed: No

**`frontend/node_modules/`:**
- Purpose: npm dependencies
- Generated: Yes
- Committed: No

---

*Structure analysis: 2026-03-22*
