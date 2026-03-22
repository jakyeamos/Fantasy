# Coding Conventions

**Analysis Date:** 2026-03-22

## Naming Patterns

**Files (Python):**
- Snake_case for all modules: `scorecard_engine.py`, `trade_repo.py`, `pick_engine.py`
- Modules follow `{noun}_engine.py`, `{noun}_repo.py`, `{noun}_service.py` suffixes that signal role
- Router files are flat by domain name: `dashboard.py`, `trade.py`, `picks.py`
- Constants modules always named `constants.py` inside their package

**Files (TypeScript):**
- PascalCase for React component files: `LeagueCard.tsx`, `EvaluationOutputPanel.tsx`
- camelCase for non-component modules: `queries.ts`, `types.ts`, `utils.ts`, `theme.ts`
- Route files use TanStack Router file-based convention: `league.$leagueId.tsx`, `trades.tsx`
- UI primitives live under `src/components/ui/`
- Domain components live under `src/components/{domain}/` (e.g. `trade/`, `picks/`, `rookie/`, `draft-room/`)

**Python Functions and Methods:**
- `snake_case` throughout
- Private helpers prefixed with single underscore: `_clamp01`, `_loads`, `_gather_inputs`, `_score_win_now`
- Public API of engines uses descriptive verbs: `compute`, `compute_all`, `compute_batch`, `evaluate`, `generate`, `build`
- Repo methods named `get_*`, `upsert_*`, `replace_*`

**TypeScript Functions:**
- `camelCase` for functions: `formatModelLabel`, `assetKey`, `appendUniqueAsset`, `fetchJson`
- Private/module-local helpers use underscore prefix: `_override_conn` (test files only)
- React components are PascalCase: `LeagueCard`, `DimensionScoreRow`

**Python Classes:**
- PascalCase: `ScorecardEngine`, `TradeEngine`, `ValuationEngine`, `PickEngine`, `ProfilingRepo`
- Pydantic models are PascalCase: `TradeRequest`, `TradeAsset`, `DimensionScore`, `ManagerProfile`
- Settings class: `Settings` (singleton via `get_settings()`)

**TypeScript Interfaces/Types:**
- PascalCase interfaces: `DashboardLeagueSummary`, `TradeEvaluation`, `DimensionScore`
- `type` aliases for union types: `TimingLabel`, `AssetBucket`, `QueryTarget`
- Interface names match Python Pydantic model names exactly to ensure API contract parity

**Constants:**
- Python: `UPPER_SNAKE_CASE` for module-level constants: `ROUND_WEIGHTS`, `SCORECARD_FIELDS`, `RECENT_EXPLOIT_WINDOW_DAYS`
- TypeScript: `UPPER_SNAKE_CASE` for arrays of tuples or config: `DIMENSIONS`, `SCORECARD_FIELDS`

## Code Style

**Python Formatting:**
- No `.prettierrc` or `ruff.toml` detected; formatting follows PEP 8 implicitly
- Lines are generally kept under 100 chars; long SQL strings use triple-quoted blocks with indentation
- `from __future__ import annotations` appears at top of all engine and router files
- Trailing comma style used in multi-line argument lists

**TypeScript Formatting:**
- No `.eslintrc` or `biome.json` present; enforced via TypeScript strict mode (`"strict": true` in `tsconfig.app.json`)
- Two-space indentation, double quotes for JSX attributes, no semicolons at end of lines (where consistent)
- Path alias `@/` resolves to `./src/` (configured in `vite.config.ts` and `tsconfig.app.json`)

## Import Organization

**Python order:**
1. `from __future__ import annotations` (when used)
2. Standard library (`json`, `math`, `collections`, `datetime`)
3. Third-party (`duckdb`, `fastapi`, `pydantic`)
4. Internal package (`from fantasy.{module} import ...`)

**TypeScript order:**
1. React and third-party libraries (`react`, `@tanstack/react-query`, `@tanstack/react-router`)
2. Internal API types and query helpers (`@/api/types`, `@/api/queries`)
3. Component imports (`@/components/...`)
4. Local utilities (`@/lib/utils`)

**Path Aliases:**
- Python: no aliases; all imports use `fantasy.{subpackage}.{module}`
- TypeScript: `@/` maps to `src/` — use `@/api/types`, `@/components/trade/DimensionScoreRow`, etc.

## Error Handling

**Python Patterns:**
- Routers raise `HTTPException` for not-found and validation errors
- Engines raise `ValueError` for missing required data (e.g., `raise ValueError(f"league not found: {league_id}")`)
- Service-layer startup tasks catch all `Exception` and log with `logger.exception(...)` — never re-raise from lifespan
- HTTP client retries handled by `tenacity` decorator on `_get` in `SleeperClient` — 5 attempts, exponential backoff
- JSON parsing uses defensive `_loads(raw, fallback)` helper pattern in engines that read stored JSON blobs
- `None`-safe patterns: `COALESCE` in SQL, `or fallback` in Python

**TypeScript Patterns:**
- API layer raises `Error` on non-OK response: `throw new Error(\`Request failed: ${path}\`)`
- Route components render an error state paragraph when `query.isError || !query.data`
- Loading states render `<Skeleton>` components while queries are pending

## Logging

**Framework:** Python `logging` module (stdlib)

**Patterns:**
- Module-level logger: `logger = logging.getLogger(__name__)` in `main.py` and service files
- Log startup outcomes at `INFO`: `logger.info("Loaded %s ADP baseline rows.", loaded)`
- Log unexpected failures at `EXCEPTION` (includes traceback): `logger.exception("Failed ...")`
- No structured logging library; plain string messages with `%s` formatting style

## Comments

**When to Comment:**
- Module-level docstrings not observed consistently — inline comments used sparingly for non-obvious logic
- SQL is inline in method bodies without comments; complex queries rely on descriptive variable names
- No JSDoc/TSDoc decorators observed; TypeScript types are self-documenting via `interface` definitions

## Function Design

**Size:** Engine scoring methods are typically 10–30 lines. Helper functions (`_clamp01`, `_loads`) are 1–5 lines.

**Parameters:**
- Engine constructors take a single `conn: duckdb.DuckDBPyConnection`
- Scoring methods receive `(inputs, inputs_map)` pairs where `inputs_map` provides league-relative context
- React component props are typed via inline `{ prop: Type }` destructuring, never via separate `Props` type alias

**Return Values:**
- Python engines return typed dataclasses or Pydantic models, never raw dicts
- Repository methods return `list[dict]` rows for use in `Model(**row)` pattern
- TypeScript query functions return typed `Promise<T>` via `queryOptions`

## Module Design

**Python Exports:**
- No `__all__` declarations; each module exposes what is imported downstream
- Engines, repos, and services are classes, not standalone functions
- Router modules expose a single `router = APIRouter(...)` instance

**Python Package Pattern:**
- `src/fantasy/{domain}/` packages contain: `models.py`, `constants.py`, `{noun}_engine.py`, `{noun}_repo.py`
- Example: `src/fantasy/trade/` has `models.py`, `trade_engine.py`, `trade_repo.py`, `reroute_engine.py`, `package_builder.py`

**TypeScript Barrel Files:**
- Not used; components import from one another directly
- All API types centralized in `src/api/types.ts`
- All query definitions centralized in `src/api/queries.ts`

## Dependency Injection (FastAPI)

- `Depends(get_read_db_conn)` for read-only routes; `Depends(get_write_db_conn)` for mutating routes
- Overridden in tests with `app.dependency_overrides[get_read_db_conn] = _override_conn(db)`
- Settings injected via `get_settings()` (cached `@lru_cache`); `monkeypatch.setenv` + `get_settings.cache_clear()` used in tests to override

---

*Convention analysis: 2026-03-22*
