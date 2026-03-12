# Stack Research

**Domain:** Local web app — Python analytics backend + React dashboard frontend (dynasty fantasy football intelligence)
**Researched:** 2026-03-11
**Confidence:** HIGH (core stack verified via PyPI, npm, and official docs; supporting libraries MEDIUM via multiple WebSearch sources)

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.12+ | Backend runtime | 3.12 is the current LTS-equivalent stable release; 3.13 is out but ecosystem compatibility trails slightly. Required for modern typing features used by FastAPI and SQLModel. |
| FastAPI | 0.135.1 | HTTP API server + data endpoints | Fastest Python web framework for local API serving. Auto-generates OpenAPI docs. Async-native — critical for non-blocking Sleeper API ingestion alongside serving dashboard requests. Pydantic-native request/response validation. Overtook Flask in GitHub stars (79k vs 68k) as of late 2024. |
| Uvicorn | 0.34+ | ASGI server (runs FastAPI) | FastAPI's recommended production-grade ASGI server. Ships as `fastapi[standard]` — no separate install needed. Sub-millisecond local response times. |
| DuckDB | 1.5.0 | Primary analytics + persistence store | In-process OLAP database — no server daemon, single `.duckdb` file, zero infrastructure overhead. 17x faster than pandas for aggregations. Native Python DataFrame zero-copy integration. Columnar storage is purpose-built for the query patterns this system needs: multi-league aggregations, historical snapshots, player value time series, pick capital calculations. The correct choice for this workload over SQLite (row-oriented, OLTP) and PostgreSQL (server required, overkill for single-user local). |
| SQLModel | 0.0.22+ | ORM + schema definition layer over DuckDB | Built by the FastAPI author (Sebastián Ramírez) on top of SQLAlchemy + Pydantic. Single class definition serves as Pydantic validation model AND database table schema. Eliminates the dual-model boilerplate of SQLAlchemy + Pydantic separately. Perfect FastAPI integration — response models and DB models are the same type. |
| Polars | 1.38.1 | In-memory DataFrame analytics engine | Rust-built, multi-threaded, Arrow-backed. 5–10x faster than pandas on typical workloads; lazy execution with query optimization. Use for the analytics pipeline: scoring engine computations, trade evaluation logic, manager behavior aggregation, prospect feature modeling. Polars reads/writes DuckDB natively via Arrow. Prefer Polars over pandas for all new analytical code in this system. |
| pandas | 2.2+ | Interop and ecosystem bridge | Not the primary analytics tool, but necessary for compatibility with scikit-learn, some visualization libraries, and legacy code paths. Keep as a supporting dependency; don't use for new analytical logic. |
| React | 19.2 | Frontend UI framework | React 19.2 is the current stable. Dashboard-centric UI pattern maps naturally to React's component model. Massive ecosystem — every charting, table, and UI library targets React first. |
| Vite | 6.x | React build tool + dev server | Industry standard for React apps since 2023; CRA is effectively abandoned. Native ES modules for instant dev startup. Proxies frontend requests to FastAPI backend during development cleanly. Vite 6 released November 2024; Node 18/20/22 support. |
| TypeScript | 5.x | Type safety for React frontend | Non-negotiable for a data-heavy dashboard. Sleeper API responses are complex nested JSON — TypeScript interfaces prevent silent data shape bugs. Vite has zero-config TypeScript support via esbuild. |

---

### Supporting Libraries

#### Python Backend

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | 0.28+ | Async HTTP client for Sleeper API | Use instead of `requests` in all FastAPI async contexts. `requests` is synchronous and blocks the event loop. `httpx` provides `AsyncClient` that works with `async/await` natively. Sleeper's player endpoint is ~5MB — async fetch prevents blocking the entire server. |
| APScheduler | 3.10+ | Scheduled background data ingestion | Runs cron-style refresh jobs (e.g., "sync league data every 6 hours") inside the FastAPI process via `AsyncScheduler`. FastAPI's built-in `BackgroundTasks` cannot repeat on a schedule — APScheduler fills this gap without requiring a separate Celery/Redis stack. |
| Alembic | 1.14+ | Database schema migrations | Manages DuckDB schema evolution across versions. Works with SQLModel/SQLAlchemy. Generates versioned migration scripts. Critical once Phase 1 is live — schema will change across phases and you cannot afford data loss. |
| pydantic-settings | 2.x | Config management | Reads `.env` files and environment variables with full type validation. Use for database paths, API base URLs, debug flags. Ships with Pydantic v2 ecosystem. |
| scikit-learn | 1.6+ | ML/clustering for prospect research | Phase 4: archetype clustering, historical comp scoring, hit-rate bucket models. The go-to for classical ML in Python. No need for PyTorch/TensorFlow for these workloads — decision trees, k-means, logistic regression are sufficient for dynasty prospect modeling. |
| pytest + pytest-asyncio | latest | Testing backend logic | Async-aware pytest runner. Needed to test async FastAPI routes and async ingestion jobs. |

#### React Frontend

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| TanStack Query (React Query) | 5.x | Server state management | Handles all data fetched from the FastAPI backend: caching, background refetch, stale-while-revalidate, loading/error states. Eliminates manual `useEffect` + `useState` data fetching patterns. The correct tool for "data that lives on the server" (league data, scores, player values). Use for every API call to FastAPI. |
| Zustand | 5.x | Client-side UI state | Manages UI-only state: selected league, active filters, sidebar collapsed state, draft room selections. Does not replace TanStack Query — they solve different problems. Use Zustand for what the user has done; use TanStack Query for what the backend knows. |
| shadcn/ui | latest | Component primitives | Copy-paste component library built on Radix UI + Tailwind. Cards, tables, dialogs, dropdowns, tooltips — all accessible and unstyled enough to theme. The correct choice over MUI or Ant Design because: zero runtime overhead, full ownership of source, Tailwind-native. Install only what you use. |
| Tailwind CSS | 4.x | Styling | Utility-first CSS. Works natively with shadcn/ui. Produces minimal CSS bundles. No CSS-in-JS runtime overhead. |
| Recharts | 3.x | Data visualization / charting | React-native SVG charts built on D3 internals. Correct balance of ease-of-use and flexibility for this domain. Line charts (value history), bar charts (sub-scores), radar charts (team profile), scatter plots (manager behavior). shadcn/ui ships a chart component layer on top of Recharts — use that for consistency. Recharts 3.8 released March 2026. |
| React Router | 6.x | Client-side routing | Navigation between league dashboard, team detail, trade evaluator, and prospect views. v6 is the current stable API (no v7 breaking changes needed for a local SPA). |
| TanStack Table | 8.x | Data tables | High-performance headless table for roster tables, prospect boards, trade history, pick capital views. Pairs with shadcn/ui table primitives for rendering. Handles sorting, filtering, and pagination without re-renders. |

---

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| uv | Python package manager + venv | Replaces pip + virtualenv. Rust-based, dramatically faster installs. `uv sync` is the 2025 standard for Python project setup. Use `pyproject.toml` as the single source of truth for deps. |
| pyproject.toml | Python project manifest | Single file for dependencies, dev dependencies, scripts, and tool config (ruff, pytest). Replaces `requirements.txt` + `setup.py`. |
| Ruff | Python linter + formatter | Replaces flake8 + black + isort. Rust-based, 100x faster. Zero-config sensible defaults. Enforces consistent code style across the analytics engine. |
| ESLint + Prettier | JS/TS linting + formatting | Standard Vite React TypeScript template includes ESLint. Add Prettier for consistent formatting. |
| Vitest | Frontend unit testing | Vite-native test runner. Same config as Vite. Use for testing analytics utility functions and React component logic. |

---

## Installation

```bash
# --- Python backend ---
# Create project with uv
uv init fantasy-backend
cd fantasy-backend
uv add "fastapi[standard]" uvicorn duckdb "sqlmodel>=0.0.22" polars pandas httpx apscheduler alembic pydantic-settings scikit-learn
uv add --dev pytest pytest-asyncio ruff

# --- React frontend ---
npm create vite@latest fantasy-frontend -- --template react-ts
cd fantasy-frontend
npm install

# Core runtime
npm install @tanstack/react-query @tanstack/react-table zustand react-router-dom recharts

# UI
npm install tailwindcss @tailwindcss/vite
npx shadcn@latest init

# Dev
npm install -D vitest @vitest/ui prettier eslint-config-prettier
```

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Web framework | FastAPI | Flask | Flask is synchronous by default; async support requires extensions. No built-in type validation. FastAPI's Pydantic integration is essential for this system's data shapes. |
| Web framework | FastAPI | Django | Django is a full-stack monolith (templates, ORM, admin, auth) — 90% of it unused for a Python API + React SPA setup. Too heavy, too opinionated in the wrong direction. |
| Database | DuckDB | SQLite | SQLite is row-oriented (OLTP). This system is almost entirely analytical queries: aggregations, time series, cross-league joins. SQLite is 10–17x slower for these patterns. DuckDB is the correct OLAP choice. |
| Database | DuckDB | PostgreSQL | PostgreSQL requires a running server daemon — adds infrastructure complexity for a local single-user app. No benefit over DuckDB for this scale and deployment model. |
| DataFrame | Polars | pandas (primary) | pandas is single-threaded and memory-inefficient. Polars is multi-threaded, lazily evaluated, and 5–10x faster. Pandas remains as an interop dependency but should not be the primary analytics engine. |
| ORM | SQLModel | SQLAlchemy (raw) | SQLAlchemy alone requires separate Pydantic schemas for FastAPI validation, creating dual-model boilerplate. SQLModel unifies both. SQLAlchemy is still the underlying engine — you can drop down to it when needed. |
| Build tool | Vite | Create React App | CRA is deprecated and unmaintained. Webpack-based, slow, incompatible with modern React. Never use for new projects. |
| Charting | Recharts | Nivo | Nivo is visually polished but poorly documented and less adopted than Recharts. Debugging issues is painful. Recharts has broader community support and integrates with shadcn/ui's chart primitives. |
| Charting | Recharts | D3 (direct) | D3 requires imperative DOM manipulation, fighting against React's declarative model. Use only if Recharts proves too limiting for a specific chart type. |
| State (server) | TanStack Query | Redux Toolkit Query | RTK adds Redux boilerplate this project does not need. TanStack Query is 40% smaller bundle, simpler API, same caching capabilities. |
| HTTP client | httpx | requests | `requests` is synchronous — blocks the FastAPI event loop when used in async route handlers. `httpx` is a drop-in replacement with async support. |
| Scheduling | APScheduler | Celery + Redis | Celery requires Redis or RabbitMQ as a message broker — unnecessary infrastructure for a single-user local app. APScheduler runs in-process with zero external dependencies. |
| Sleeper API client | Custom httpx wrapper | sleeper-api-wrapper (PyPI) | The original wrapper (SwapnikKatkoori) is abandoned (last commit 2019). The dtsong fork (v1.2.1, Nov 2025) is actively maintained but wraps `requests` synchronously. Build a thin async httpx client instead — the Sleeper API is simple REST, not complex enough to need a full wrapper library, and async is required for this architecture. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Create React App (CRA) | Deprecated, unmaintained since 2022. Webpack-based, 30–60s cold starts, broken ecosystem. | Vite 6 |
| `requests` library in FastAPI async routes | Synchronous I/O blocks the entire ASGI event loop. Degrades all concurrent requests during Sleeper API calls. | `httpx` with `AsyncClient` |
| pandas as primary analytics engine | Single-threaded, copy-on-write behavior is subtle, 5–10x slower than Polars for aggregations and joins. | Polars (use pandas only for ML library interop) |
| Redux (vanilla or RTK) for all state | Redux forces all state — including server data — through a single store, requiring manual cache invalidation. TanStack Query solves server state better with zero boilerplate. | TanStack Query (server state) + Zustand (UI state) |
| SQLite as the analytics store | Row-oriented storage is the wrong architecture for analytical queries. Window functions, aggregations, and cross-league joins will be 10–17x slower. | DuckDB |
| PostgreSQL for local-only deployment | Requires a running server process, pg_hba.conf, connection pooling — all unnecessary complexity for a single-user local app with no concurrency concerns. | DuckDB |
| Material UI (MUI) or Ant Design | Both ship full component runtimes with significant bundle weight (~500KB+). Theming requires fighting the library's opinion. | shadcn/ui (zero runtime, you own the source) |
| Hardcoding player data | Sleeper's player endpoint (~5MB) should be cached locally and refreshed weekly — not fetched on every request. Rate limit is 1000 calls/min; a naive implementation will hit it. | Cache `/v1/players/nfl` to DuckDB on a weekly APScheduler job |
| Streamlit or Dash for the frontend | Streamlit/Dash produce Python-rendered UIs with limited interactivity and no proper component model. This system needs complex dashboard layouts, multi-pane views, and reactive client state — React is the correct tool. | React + Vite |

---

## Stack Patterns by Variant

**For the Sleeper API ingestion layer:**
- Build a thin `SleeperClient` class using `httpx.AsyncClient` with a shared session
- Cache the 5MB player endpoint to DuckDB with a `last_synced` timestamp; refresh weekly via APScheduler
- All other endpoints (leagues, rosters, transactions) are fast — fetch on demand per user action
- Never couple the ingestion layer to the analysis engines — ingest into raw tables, transform separately

**For the analytics engines (scoring, trade eval, prospect):**
- Use Polars for all computation; return Arrow batches directly to DuckDB or Pydantic models to FastAPI
- Structure engines as pure functions: `(inputs: LeagueSnapshot) -> EngineOutput` — no side effects, fully testable
- Persist engine outputs to DuckDB snapshot tables for historical comparison (Phase 5 requirement)

**For the React dashboard state:**
- TanStack Query for everything that comes from the FastAPI backend
- Zustand for: selected league ID, active view state, any pending user edits not yet saved
- Do not put server data in Zustand — it creates a cache invalidation problem

**For DuckDB schema evolution:**
- Use Alembic with SQLModel to generate migration scripts
- DuckDB supports `ALTER TABLE ADD COLUMN` and most standard DDL — Alembic works cleanly
- Version the schema from Phase 1 forward; do not use `create_all()` in production paths

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| FastAPI 0.135.x | Pydantic v2, SQLModel 0.0.22+ | FastAPI dropped Pydantic v1 support in 0.100+. SQLModel requires Pydantic v2. All three must be v2-aligned. |
| SQLModel 0.0.22+ | SQLAlchemy 2.0+ | SQLModel requires SQLAlchemy 2.0 — the async-first rewrite. Do not install SQLAlchemy 1.x. |
| Polars 1.38.x | DuckDB 1.5.0 via Arrow | Polars and DuckDB share Apache Arrow format. Use `duckdb.from_arrow()` and `polars.from_arrow()` for zero-copy transfer. |
| React 19.2 | TanStack Query v5, Zustand v5 | TanStack Query v5 and Zustand v5 both require React 18+. All are compatible with React 19.2. |
| Vite 6.x | React 19, TypeScript 5.x | Vite 6 requires Node 18, 20, or 22. Drops Node 21. Uses esbuild for TS compilation — no `ts-node` needed. |
| shadcn/ui (latest) | Tailwind 4.x, React 19 | shadcn/ui ships Recharts as its charting primitive. Install shadcn chart components and use Recharts directly — they are the same library. |
| Recharts 3.x | React 18+ | Recharts 3.x drops React 16/17 support. Compatible with React 19.2. |

---

## Sources

- PyPI — FastAPI 0.135.1 (verified 2026-03-11): https://pypi.org/project/fastapi/
- PyPI — DuckDB 1.5.0 (verified 2026-03-11): https://pypi.org/project/duckdb/
- PyPI — Polars 1.38.1 (verified 2026-03-11): https://pypi.org/project/polars/
- React official blog — React 19.2 stable (October 2025): https://react.dev/blog/2025/10/01/react-19-2
- Vite official blog — Vite 6.0 release (November 2024): https://vite.dev/blog/announcing-vite6
- Sleeper API docs — endpoints and rate limiting: https://docs.sleeper.com/
- dtsong/sleeper-api-wrapper — v1.2.1 active fork (November 2025): https://github.com/dtsong/sleeper-api-wrapper
- SwapnikKatkoori/sleeper-api-wrapper — original, ABANDONED: https://github.com/SwapnikKatkoori/sleeper-api-wrapper
- MotherDuck — DuckDB vs SQLite comparison: https://motherduck.com/learn-more/duckdb-vs-sqlite-databases/
- LogRocket — Best React chart libraries 2025: https://blog.logrocket.com/best-react-chart-libraries-2025/
- JetBrains — Django vs Flask vs FastAPI (February 2025): https://blog.jetbrains.com/pycharm/2025/02/django-flask-fastapi/
- Zustand v5 release: https://github.com/pmndrs/zustand
- TanStack Query docs: https://tanstack.com/query/latest
- shadcn/ui: https://ui.shadcn.com/
- APScheduler + FastAPI integration: https://rajansahu713.medium.com/implementing-background-job-scheduling-in-fastapi-with-apscheduler-6f5fdabf3186
- httpx async docs: https://www.python-httpx.org/async/
- SQLModel docs: https://sqlmodel.tiangolo.com/

---

*Stack research for: Dynasty Fantasy Football Front Office OS — Python + React local web app*
*Researched: 2026-03-11*
