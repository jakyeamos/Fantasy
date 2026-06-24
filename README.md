# Fantasy

Fantasy is a local-first dynasty fantasy football intelligence app with:

- a FastAPI backend for ingestion, analytics, and decision engines
- a React + Vite frontend for dashboards, trade tools, draft room, and portfolio views
- a DuckDB data store persisted at `data/fantasy.duckdb`

## Repository Layout

- `backend` - FastAPI service, ingestion workflows, valuation/intelligence logic, Alembic migrations, Python tests
- `frontend` - React 19 + TanStack Router + React Query UI
- `data` - local database and data artifacts

## Tech Stack

- Backend: Python 3.12+, FastAPI, SQLAlchemy, Alembic, DuckDB
- Frontend: React 19, TypeScript, Vite, TanStack Router, React Query, Tailwind CSS

## Prerequisites

- Python 3.12+
- Node.js 20+ and pnpm
- `uv` (recommended for backend dependency management)

## Quick Start

### 1) Install dependencies

```bash
cd backend
uv sync
cd ../frontend
pnpm install
```

### 2) Start the local app

```bash
./dev.sh
```

The launcher applies local DuckDB migrations before the backend boots, then starts the API at `http://localhost:8000` and the app at `http://localhost:5173`.

The Vite dev server proxies `/api/*` to `http://localhost:8000`, so local frontend requests work without extra API host configuration.

## Backend Development

Run tests:

```bash
cd backend
uv run pytest
```

Useful backend environment variables (loaded from repo root `.env` when present):

- `FANTASY_DB_PATH` (default: `data/fantasy.duckdb`)
- `FANTASY_PORTFOLIO_OWNER_DISPLAY_NAME`
- `FANTASY_PORTFOLIO_OWNER_ID`
- `FANTASY_DEV_AUTO_REFRESH` (`true`/`false`)
- `FANTASY_DEV_AUTO_REFRESH_LEAGUES` (comma-separated league IDs)
- `FANTASY_DEV_AUTO_REFRESH_INGEST_MODE` (`skip`, `incremental`, `full`)
- `FANTASY_DEV_AUTO_REFRESH_SNAPSHOTS` (`true`/`false`)

For dev auto-refresh behavior and personalization examples, see `backend/README.md`.

## Frontend Development

Build and type-check:

```bash
cd frontend
pnpm build
```

## Database Migrations

Apply latest migrations:

```bash
cd backend
uv run alembic upgrade heads
```

Create a new migration:

```bash
cd backend
uv run alembic revision -m "describe change"
```
