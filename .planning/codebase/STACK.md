# Technology Stack

**Analysis Date:** 2026-03-22

## Languages

**Primary:**
- Python 3.12+ (required) / 3.14.2 (local dev) - Backend API, data ingestion, intelligence engines
- TypeScript 5.9.3 - Frontend React application

**Secondary:**
- SQL (DuckDB dialect) - All database queries written as raw SQL strings, not ORM expressions

## Runtime

**Environment:**
- Python: >=3.12 (enforced in `backend/pyproject.toml`)
- Node.js: 24.12.0 (local dev, no `.nvmrc` constraint)

**Package Manager:**
- Python: `hatchling` build backend, `pip`/`uv` for install
  - Lockfile: Not present (no `requirements.lock` or `uv.lock`)
- Node: `npm` with `package-lock.json`
  - Lockfile: `frontend/package-lock.json` (present)

## Frameworks

**Backend Core:**
- FastAPI >=0.115 - REST API framework (`backend/src/fantasy/main.py`)
- Pydantic >=2.0 - Request/response model validation
- pydantic-settings >=2.4 - Environment config via `Settings` class (`backend/src/fantasy/config.py`)
- Uvicorn >=0.30 - ASGI server

**Frontend Core:**
- React 19.2.0 - UI framework
- TanStack Router 1.168.1 - File-based routing with auto code splitting (`frontend/src/routeTree.gen.ts`)
- TanStack Query 5.91.3 - Server state and data fetching (`frontend/src/api/queries.ts`)

**Styling:**
- Tailwind CSS 4.2.2 - Utility-first CSS (configured via `@tailwindcss/vite` Vite plugin)
- clsx 2.1.1 + tailwind-merge 3.3.1 - Conditional class merging (`frontend/src/lib/utils.ts`)
- lucide-react 0.511.0 - Icon library

**Build/Dev:**
- Vite 8.0.1 - Frontend bundler and dev server (`frontend/vite.config.ts`)
- `@tanstack/router-plugin` 1.167.2 - Route tree code generation
- TypeScript strict mode, ES2022 target

**Testing:**
- pytest >=8 - Backend test runner (`backend/pyproject.toml`)
- pytest-asyncio >=0.23 - Async test support, `asyncio_mode = "auto"`
- pytest-httpx >=0.30 - HTTP mock for `httpx` in tests
- No frontend test framework detected

**Database ORM/Migration:**
- SQLAlchemy >=2.0 - Schema definitions only (`backend/src/fantasy/db/models.py`), NOT used for query execution
- Alembic >=1.13 - Database migrations (`backend/alembic/`)
- DuckDB 1.5.0 - Embedded analytical database, all queries via raw `duckdb.DuckDBPyConnection`
- duckdb-engine 0.17.0 - SQLAlchemy dialect for Alembic migrations

## Key Dependencies

**Critical:**
- `duckdb==1.5.0` - Pinned exact version; primary data store at `data/fantasy.duckdb`
- `httpx>=0.27` - Async HTTP client for Sleeper API calls (`backend/src/fantasy/ingestion/sleeper_client.py`)
- `tenacity>=8.2` - Retry logic on Sleeper API with exponential backoff (5 attempts, 2–30s)
- `polars>=1.0` - DataFrame operations for NFL stats ingestion (`backend/src/fantasy/ingestion/nfl_data_loader.py`)
- `nfl-data-py==0.3.3` - NFL weekly stats import; only installed on Python <3.13

**Infrastructure:**
- `@tanstack/react-query-devtools` - Query inspection in dev
- `@vitejs/plugin-react` 5.1.0 - React fast refresh in Vite

## Configuration

**Environment:**
- All backend settings loaded via `pydantic-settings` from `.env` at repo root (existence confirmed)
- Env prefix: `FANTASY_` (e.g., `FANTASY_DB_PATH`, `FANTASY_PORTFOLIO_OWNER_ID`)
- Key settings (`backend/src/fantasy/config.py`):
  - `FANTASY_DB_PATH` - Path to DuckDB file (default: `data/fantasy.duckdb`, supports `:memory:`)
  - `FANTASY_PORTFOLIO_OWNER_ID` - Sleeper user ID for the portfolio owner
  - `FANTASY_PORTFOLIO_OWNER_DISPLAY_NAME` - Display name override
  - `FANTASY_INGEST_LOCK_TIMEOUT` - Lock timeout in seconds (default: 300)
  - `FANTASY_DEV_AUTO_REFRESH` - Enable auto-refresh on startup (default: false)
  - `FANTASY_DEV_AUTO_REFRESH_LEAGUES` - Comma-separated league IDs for auto-refresh
  - `FANTASY_DEV_AUTO_REFRESH_INGEST_MODE` - `skip` | `incremental` | `full`
  - `FANTASY_DEV_AUTO_REFRESH_SNAPSHOTS` - Include snapshots in auto-refresh

**Build:**
- `frontend/vite.config.ts` - Vite config with `/api` proxy to `http://localhost:8000`
- `frontend/tsconfig.app.json` - TypeScript strict mode, `@` path alias pointing to `frontend/src/`
- `backend/alembic.ini` - Alembic config, `sqlalchemy.url = duckdb:///../data/fantasy.duckdb`
- `backend/pyproject.toml` - Build config with hatchling, packages from `src/fantasy`

## Platform Requirements

**Development:**
- Python >=3.12 (note: `nfl-data-py` only installs on <3.13; NFL stats load path is skipped on 3.13+)
- Node.js >=20 recommended (24.x in use locally)
- DuckDB file at `data/fantasy.duckdb` (auto-created on first run)
- `.env` file at repo root with at minimum `FANTASY_PORTFOLIO_OWNER_ID`

**Production:**
- Single-process deployment; no distributed or multi-process assumptions
- DuckDB is embedded — no separate database server required
- Frontend served statically from `frontend/dist/` after `npm run build`
- Backend served via `uvicorn fantasy.main:app`

---

*Stack analysis: 2026-03-22*
