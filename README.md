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

The process probes are `http://127.0.0.1:8000/healthz` for liveness and
`http://127.0.0.1:8000/readyz` for DuckDB/runtime-table readiness. League data
freshness remains available at `/health/{league_id}`.

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

## Fresh Intelligence Morning Brief

After applying migrations, build the prepared Today briefing on demand:

```bash
cd backend
uv run python -m fantasy.intelligence run --scheduled
```

The idempotent pipeline discovers structured and configured public evidence,
validates and deduplicates events, rebuilds affected league consequences, and
publishes today's brief. It never submits a trade, waiver, lineup, or other
league action. App startup does not call these external sources automatically;
Today offers an explicit run when no current brief exists.

Optional configuration (credentials remain environment-only and are never
stored in DuckDB):

- `FANTASY_INTELLIGENCE_PUBLIC_FEEDS`: comma-separated public feed/page URLs
- `FANTASY_INTELLIGENCE_BROWSER_ENABLED`: enable guarded Playwright fallback
- `FANTASY_INTELLIGENCE_BROWSER_EXECUTABLE_PATH`: optional local browser path
- `FANTASY_INTELLIGENCE_EXTRACTOR_PROVIDER`: `none` (deterministic default) or
  `openai_compatible`
- `FANTASY_INTELLIGENCE_EXTRACTOR_BASE_URL`,
  `FANTASY_INTELLIGENCE_EXTRACTOR_MODEL`, and
  `FANTASY_INTELLIGENCE_EXTRACTOR_API_KEY`: optional user-selected model

Public fetching rejects local/private network targets, validates redirects,
honors robots controls and rate limits, and never bypasses authentication,
paywalls, CAPTCHAs, or anti-bot responses. Full page bodies remain only in the
ignored seven-day local cache at `data/cache/intelligence`; durable evidence is
normalized and excerpted.

An opt-in 8:00 AM macOS template is provided at
`ops/launchd/com.jakyeamos.fantasy-morning-brief.plist.example`. Replace
`__FANTASY_REPO__` in a copy before use. Installation into
`~/Library/LaunchAgents` is intentionally not automated and requires explicit
user approval.

Local v2 endpoints are documented in OpenAPI and include refresh, public-link
analysis, today's brief, event evidence/impact detail, review, and feedback
under `/api/v2`.

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

## Disposable Database Baselines

Never use the primary local database as a migration or refresh test target.
Create a copied database and inventory manifest instead:

```bash
cd backend
uv run python -m fantasy.tools.db_baseline copy \
  --source ../data/fantasy.duckdb \
  --destination /private/tmp/fantasy-baseline.duckdb \
  --manifest /private/tmp/fantasy-baseline.manifest.json
```

The command copies an adjacent DuckDB WAL when present, records row counts,
columns, candidate stable keys, hashes, and the Alembic version, and refuses to
overwrite an existing target unless `--force` is supplied. Restore only into an
explicit disposable target with the same command shape using `restore`.
