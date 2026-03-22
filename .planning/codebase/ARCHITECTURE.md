# Architecture

**Analysis Date:** 2026-03-22

## Pattern Overview

**Overall:** Full-stack SPA + REST API with domain-driven backend modules

**Key Characteristics:**
- React SPA (Vite + TanStack Router) communicates with a FastAPI backend via a proxied `/api` prefix
- Backend organizes logic into feature domains: each domain has `models.py`, a `*_engine.py` or `*_service.py`, and a `*_repo.py`
- Single embedded DuckDB file is the sole persistent store — no external database server
- Computation is on-demand with lazy cache-aside: results are persisted to DuckDB on first compute, read from DB on subsequent calls
- Alembic migrations manage schema evolution (10 migrations at time of audit)

## Layers

**API / Routing Layer:**
- Purpose: HTTP request handling, Pydantic request/response validation, dependency injection
- Location: `backend/src/fantasy/routers/`
- Contains: One module per domain (`dashboard.py`, `trade.py`, `profiling.py`, `picks.py`, `rookie_board.py`, `draft_room.py`, `ingest.py`, `intelligence.py`, `snapshots.py`, `corrections.py`, `health.py`)
- Depends on: Service/Engine layer, Repo layer, `routers/deps.py`
- Used by: Frontend via HTTP

**Service / Engine Layer:**
- Purpose: Core business logic, computation orchestration
- Location: `backend/src/fantasy/<domain>/`
- Contains: `*_service.py` (pipeline orchestration) or `*_engine.py` (computation) per domain
- Key classes: `IngestService`, `IntelligenceService`, `ScorecardEngine`, `DirectionEngine`, `ValuationEngine`, `TradeEngine`, `ProfilingEngine`, `PickEngine`, `RookieEngine`
- Depends on: Repo layer, sibling engines, domain models, constants
- Used by: Router layer, `startup_tasks.py`

**Repository Layer:**
- Purpose: All raw SQL against DuckDB; upsert, query, and persist computed results
- Location: `backend/src/fantasy/repositories/league_repo.py`, `backend/src/fantasy/<domain>/<domain>_repo.py`
- Contains: `LeagueRepo`, `TradeRepo`, `ProfilingRepo`, `PickRepo`, `RookieRepo` (via `rookie_repo.py`)
- Depends on: `db/connection.py`, `db/models.py` (SQLAlchemy Core table definitions)
- Used by: Service/Engine layer and some routers directly

**Data / Schema Layer:**
- Purpose: Table definitions and connection management
- Location: `backend/src/fantasy/db/models.py`, `backend/src/fantasy/db/connection.py`
- Contains: SQLAlchemy Core `Table` objects (not ORM), two connection factory functions
- Depends on: DuckDB, settings
- Used by: Repo layer, startup

**Domain Models:**
- Purpose: Typed Pydantic data transfer objects shared across service and router layers
- Location: `backend/src/fantasy/<domain>/models.py`
- Examples: `backend/src/fantasy/intelligence/models.py`, `backend/src/fantasy/trade/models.py`, `backend/src/fantasy/picks/models.py`
- Pattern: `BaseModel` with `ConfigDict(frozen=False)`, mirrored by matching TypeScript interfaces in `frontend/src/api/types.ts`

**Frontend Route / Page Layer:**
- Purpose: Page-level components bound to URL routes, own data fetching via TanStack Query
- Location: `frontend/src/routes/`
- Contains: One file per route segment (`index.tsx`, `league.$leagueId.tsx`, `league.$leagueId.managers.tsx`, `league.$leagueId.managers.$managerId.tsx`, `league.$leagueId.rookie-board.tsx`, `trades.tsx`, `draft-room.tsx`)
- Depends on: `api/queries.ts`, domain components
- Used by: TanStack Router via auto-generated `routeTree.gen.ts`

**Frontend Component Layer:**
- Purpose: Reusable UI components scoped to a feature domain
- Location: `frontend/src/components/<domain>/`
- Contains: Domain-scoped sub-directories (`trade/`, `picks/`, `rookie/`, `draft-room/`) plus top-level feature components and `ui/` primitives
- Depends on: `api/queries.ts`, `api/types.ts`, `lib/utils.ts`

## Data Flow

**Ingestion Flow:**

1. Frontend or startup task calls `POST /ingest/{league_id}?run_type=full|incremental`
2. `IngestService` opens a write connection, locks against concurrent runs via `ingest_runs` table
3. `SleeperClient` (async httpx) fetches league data, rosters, picks, transactions, player metadata from Sleeper API
4. `SleeperMapper` normalises raw API responses into typed dataclasses
5. `LeagueRepo` upserts normalized records into `leagues`, `rosters`, `standings`, `traded_picks`, `transactions`, `players`
6. `SnapshotService` computes a point-in-time `league_snapshots` row
7. Ingest run record is finalized in `ingest_runs` with cursor JSON

**Intelligence Computation Flow:**

1. `POST /intelligence/compute/{league_id}` triggers `IntelligenceService.compute_league()`
2. `ScorecardEngine` reads roster/player/stats data from DuckDB, produces 9-dimension `TeamScorecard` per roster
3. `DirectionEngine` classifies each scorecard into a strategic direction label (e.g., "Contender", "Rebuild")
4. `ValuationEngine` computes per-player `PlayerValue` objects with direction-aware lens scores
5. Results are persisted to `team_scorecards`, `team_directions`, `player_values` tables
6. Dashboard router reads pre-computed results; missing results trigger on-demand compute

**Trade Evaluation Flow:**

1. `POST /trade/evaluate` receives a `TradeRequest` (user assets, counterparty assets, optional third-party legs)
2. `TradeEngine` calls `TradeRepo` for scorecard, player value, and pick value data
3. Engine scores 7 `DimensionScore` dimensions (market fairness, roster fit, direction fit, timing, insulation delta, liquidity delta, manager exploit quality)
4. `StrategicDistinction` verdict is computed from composite dimension scores
5. Optional: `RerouteEngine` generates alternative deal suggestions; `PackageBuilder` proposes opening/closing offers
6. `TradeEvaluation` is returned — not persisted

**Pick Valuation Flow:**

1. `GET /picks/{league_id}` or `POST /picks/{league_id}/recompute` invokes `PickEngine`
2. `PickRepo` reads traded picks, standings, and player stats
3. `PickEngine` computes base value, timing adjustments, league-adjusted and demand-adjusted values per pick
4. Results written to `pick_values` table on recompute; read directly on GET

**State Management (Frontend):**
- TanStack Query is the sole state management mechanism — all server state is query-cached
- `staleTime` configured per query: 5 min for league detail, 1 min for manager profiles, 30 s for snapshot status
- No global client state store (no Redux, Zustand, etc.)

## Key Abstractions

**TeamScorecard:**
- Purpose: 9-dimension floating-point score representing a roster's strategic health
- Examples: `backend/src/fantasy/intelligence/models.py`, persisted in `team_scorecards` table
- Pattern: Computed by `ScorecardEngine`, consumed by `DirectionEngine`, `ValuationEngine`, dashboard router, and trade engine

**TradeAsset:**
- Purpose: Polymorphic representation of either a player or a future draft pick
- Examples: `backend/src/fantasy/trade/models.py` (Python), `frontend/src/api/types.ts` (TypeScript)
- Pattern: `asset_type: Literal["player", "pick"]` discriminant with optional fields for each type

**DimensionScore:**
- Purpose: A single trade evaluation axis with a 0–100 score, confidence level, and natural language reasoning
- Examples: `backend/src/fantasy/trade/models.py`, `frontend/src/api/types.ts`
- Pattern: 7 dimensions produce one `TradeEvaluation`

**Engine classes (stateless computation):**
- Purpose: Take a DuckDB connection on construction, expose `compute_*` methods, return Pydantic models
- Examples: `ScorecardEngine`, `DirectionEngine`, `ValuationEngine`, `TradeEngine`, `PickEngine`, `RookieEngine`, `ProfilingEngine`
- Pattern: `__init__(self, conn: duckdb.DuckDBPyConnection)` — engine does not own connection lifecycle

**Repo classes:**
- Purpose: All SQL is in repo classes; no raw SQL in engines or routers
- Examples: `LeagueRepo`, `TradeRepo`, `PickRepo`, `ProfilingRepo`
- Pattern: `__init__(self, conn: duckdb.DuckDBPyConnection)` — same connection passed in from router dependency

## Entry Points

**Backend API Server:**
- Location: `backend/src/fantasy/main.py`
- Triggers: `uvicorn fantasy.main:app` (or auto-started by dev tooling)
- Responsibilities: Registers all routers, configures CORS, runs lifespan startup tasks (ADP baseline load, optional dev auto-refresh)

**Startup Tasks:**
- Location: `backend/src/fantasy/startup_tasks.py`
- Triggers: FastAPI lifespan on server start
- Responsibilities: Schema compat migration, optional incremental ingest + intelligence compute + profiling for configured leagues

**Frontend SPA:**
- Location: `frontend/src/main.tsx`
- Triggers: Browser via `index.html` entry
- Responsibilities: Initializes TanStack Query client, creates router from generated route tree, applies theme

**DB Connection Dependency:**
- Location: `backend/src/fantasy/routers/deps.py`
- Triggers: FastAPI `Depends()` on each request
- Responsibilities: Opens a read-only or write-capable DuckDB connection, yields it, closes it after the handler returns

## Error Handling

**Strategy:** Exceptions bubble to FastAPI's default handler; routers raise `HTTPException` for known domain failures; engines raise Python exceptions caught at router level

**Patterns:**
- `IngestService` raises `RuntimeError` on concurrent run lock — caught in router as 503
- Profiling router returns 404 if `evidence_count == 0`
- `PickRepo.has_pick()` checked before single-pick GET; 404 raised if missing
- Corrections router raises 404 for unknown `correction_id`
- Engines do not raise HTTP-layer exceptions; they return domain model instances or raise standard Python errors

## Cross-Cutting Concerns

**Logging:** Standard `logging` module; `logger = logging.getLogger(__name__)` in each module; startup tasks and ingestion log at INFO/WARNING/ERROR
**Validation:** Pydantic on all request bodies and response models in routers; SQLAlchemy Core table definitions for schema structure
**Authentication:** None — CORS is open (`allow_origins=["*"]`); the app is designed for local/personal use
**Settings:** `pydantic_settings.BaseSettings` with `FANTASY_` env prefix; loaded via `get_settings()` with `@lru_cache(maxsize=1)`; reads from root `.env` file
**Database connections:** Two connection modes — `get_read_connection()` (read-only) and `get_write_connection()` (read-write); injected via `Depends(get_read_db_conn)` or `Depends(get_write_db_conn)`

---

*Architecture analysis: 2026-03-22*
