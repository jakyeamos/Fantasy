# External Integrations

**Analysis Date:** 2026-03-22

## APIs & External Services

**Fantasy Platform:**
- Sleeper API (`https://api.sleeper.app/v1`) - Primary data source for all league, roster, player, transaction, and pick data
  - SDK/Client: Custom async client at `backend/src/fantasy/ingestion/sleeper_client.py`
  - Auth: None — Sleeper's v1 API is unauthenticated for read operations
  - Retry policy: `tenacity` exponential backoff, 5 attempts, retries on HTTP 429/500/502/503/504 and `NetworkError`
  - Endpoints consumed:
    - `GET /league/{league_id}` — league metadata
    - `GET /league/{league_id}/rosters` — team rosters
    - `GET /league/{league_id}/users` — manager user data
    - `GET /league/{league_id}/traded_picks` — pick ownership
    - `GET /league/{league_id}/transactions/{week}` — weekly transactions
    - `GET /state/nfl` — current NFL week/season state
    - `GET /players/nfl` — full player registry

**NFL Statistics:**
- nfl-data-py 0.3.3 (`https://github.com/nflverse/nfl_data_py`) - Weekly player statistics import
  - Client: `NflDataPyLoader` class at `backend/src/fantasy/ingestion/nfl_data_loader.py`
  - Auth: None — open data via `nfl.import_weekly_data(years)`
  - Constraint: Only installs on Python <3.13; skipped silently on 3.13+
  - Data written to `player_stats_weekly` table via Polars DataFrame → DuckDB upsert

**ADP Baseline:**
- FantasyPros (manual CSV export) - ADP data loaded from `data/adp_baseline.csv`
  - Client: `load_adp_baseline()` function at `backend/src/fantasy/ingestion/nfl_data_loader.py`
  - Auth: None — file-based, not a live API call
  - Loaded at application startup via `lifespan` in `backend/src/fantasy/main.py`
  - Written to `player_adp_baseline` table (full replace on each load)

## Data Storage

**Databases:**
- DuckDB 1.5.0 (embedded, single-file)
  - File location: `data/fantasy.duckdb` (configurable via `FANTASY_DB_PATH`)
  - Connection: `backend/src/fantasy/db/connection.py` — `get_write_connection()` and `get_read_connection()`
  - Read-only connections used for all GET endpoints via `get_read_db_conn` FastAPI dependency (`backend/src/fantasy/routers/deps.py`)
  - Write connections used for ingest/mutation endpoints
  - Migrations: Alembic with `duckdb-engine` dialect, 10 migration files in `backend/alembic/versions/`

**Schema tables (as of migration 010):**
- `leagues` — league metadata and scoring settings
- `rosters` — team rosters with player IDs as JSON strings
- `standings` — wins/losses/points per team
- `traded_picks` — pick ownership records
- `transactions` — all trade/add/drop transactions
- `players` — player registry (ID, name, position, team, age)
- `ingest_runs` — audit log for all ingest operations
- `corrections` — user-applied data overrides
- `player_stats_weekly` — NFL weekly stats from nfl-data-py
- `player_adp_baseline` — ADP values from FantasyPros CSV
- Additional tables from migrations 004–010: intelligence output tables, snapshots, profiling tables, manager profile trade history, pick values, rookie board

**File Storage:**
- Local filesystem only — `data/` directory at repo root
- `data/fantasy.duckdb` — primary database
- `data/adp_baseline.csv` — ADP import file (manually placed)

**Caching:**
- None — no Redis, Memcached, or in-memory cache layer
- TanStack Query handles client-side stale-while-revalidate with per-query `staleTime` (5 min for dashboard/league, 1 min for profiling, 30s for snapshot status)

## Authentication & Identity

**Auth Provider:**
- None — no authentication system
- Application identifies the portfolio owner via `FANTASY_PORTFOLIO_OWNER_ID` and `FANTASY_PORTFOLIO_OWNER_DISPLAY_NAME` env vars set at startup
- All API endpoints are open (no auth middleware)
- CORS is open (`allow_origins=["*"]`) — configured in `backend/src/fantasy/main.py`

## Monitoring & Observability

**Error Tracking:**
- None — no Sentry, Datadog, or equivalent

**Logs:**
- Python stdlib `logging` module used throughout backend
- Logger instances created per module with `logging.getLogger(__name__)`
- Log level configuration via Alembic's `alembic.ini` (root: WARN, alembic: INFO)
- No structured logging format (plain text)
- No log aggregation service

## CI/CD & Deployment

**Hosting:**
- Not detected — no deployment config files (`Dockerfile`, `railway.toml`, `fly.toml`, `Procfile`, Vercel/Netlify config)
- Appears to be a local-only development tool

**CI Pipeline:**
- None detected — no `.github/workflows/`, CircleCI, or similar

## Environment Configuration

**Required env vars (from `backend/src/fantasy/config.py`):**
- `FANTASY_PORTFOLIO_OWNER_ID` — Sleeper user ID for the portfolio owner (no default; features degrade without it)
- `FANTASY_DB_PATH` — DuckDB file path (default: `data/fantasy.duckdb`)

**Optional env vars:**
- `FANTASY_PORTFOLIO_OWNER_DISPLAY_NAME` — Display name override
- `FANTASY_INGEST_LOCK_TIMEOUT` — Default 300 seconds
- `FANTASY_DEV_AUTO_REFRESH` — Default false
- `FANTASY_DEV_AUTO_REFRESH_LEAGUES` — Default empty string
- `FANTASY_DEV_AUTO_REFRESH_INGEST_MODE` — Default `incremental`
- `FANTASY_DEV_AUTO_REFRESH_SNAPSHOTS` — Default true

**Secrets location:**
- `.env` file at repo root (confirmed present, contents not read)
- No secrets management service detected

## Webhooks & Callbacks

**Incoming:**
- None — no webhook endpoints registered

**Outgoing:**
- None — all external calls are pull-based (polling Sleeper API on demand or startup)

## Frontend API Communication

**Pattern:**
- All frontend API calls go through `/api` prefix
- Vite dev server proxies `/api/*` → `http://localhost:8000/*` (strips `/api` prefix)
- HTTP client: browser `fetch` API, wrapped in `getJson<T>()` at `frontend/src/api/queries.ts`
- All queries defined as TanStack Query `queryOptions` objects in `frontend/src/api/queries.ts`
- No WebSocket or SSE connections

---

*Integration audit: 2026-03-22*
