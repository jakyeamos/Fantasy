# Codebase Concerns

**Analysis Date:** 2026-03-22

---

## Security Considerations

**CORS wildcard allows all origins:**
- Risk: Any website can make cross-origin requests to the backend API, including potentially malicious ones.
- Files: `backend/src/fantasy/main.py` (line 59: `allow_origins=["*"]`)
- Current mitigation: None — app is single-user and localhost-only in practice.
- Recommendations: Restrict to `http://localhost:5173` (or configured frontend origin) for any deployment beyond personal use.

**No authentication or authorization on any endpoint:**
- Risk: All API endpoints are fully open. Any process with network access can trigger ingests, compute league intelligence, read all league/player data, or write corrections.
- Files: All routers in `backend/src/fantasy/routers/`
- Current mitigation: Single-user personal tool with no public exposure.
- Recommendations: Add API key middleware or at minimum document that this is not safe to expose publicly.

**F-string SQL with column names (not user-controlled, but still fragile):**
- Risk: Several SQL queries interpolate column or table names via f-strings. While these values come from internal constants (not user input), any future refactor that accidentally threads user input through these paths would introduce SQL injection.
- Files:
  - `backend/src/fantasy/routers/dashboard.py` (line 179: `{best_field}` in SELECT and ORDER BY)
  - `backend/src/fantasy/intelligence/intelligence_service.py` (line 174: `{table}` in `_next_id`)
  - `backend/src/fantasy/repositories/league_repo.py` (line 26: `{table}` in `_next_id`)
  - `backend/src/fantasy/profiling/profiling_repo.py` (line 26: `{table}` in `_next_id`)
  - `backend/src/fantasy/profiling/profiling_engine.py` (lines 186, 198, 208: `{placeholders}` from `",".join("?")` — safe)
  - `backend/src/fantasy/startup_tasks.py` (line 76: `ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}`)
- Current mitigation: `best_field` is always one of a fixed set of scorecard column names; `table`/`table_name` come from internal dicts.
- Recommendations: Use allowlist validation before interpolation, especially for `best_field` in `dashboard.py`.

---

## Tech Debt

**Dual schema management system — Alembic + runtime compat patching:**
- Issue: Alembic migrations exist in `backend/alembic/versions/` (001–010) but are not applied at startup. Instead, `ensure_runtime_schema()` in `backend/src/fantasy/startup_tasks.py` manually adds only two hardcoded columns (`rosters.owner_display_name`, `manager_profiles.trade_history`) as a compatibility shim. The conftest fixture `SCHEMA_SQL` is a third independent copy of the full schema.
- Impact: Any new column added via Alembic is NOT guaranteed to exist at runtime unless `ensure_runtime_schema` is extended. Test schema and production schema can silently diverge. New phases must update three places: the migration file, `_SCHEMA_COMPAT_COLUMNS`, and `conftest.py`.
- Fix approach: Either run `alembic upgrade head` during startup, or consolidate to a single `CREATE TABLE IF NOT EXISTS` / `ALTER TABLE IF NOT EXISTS` approach and eliminate Alembic for new tables.

**`INGEST_LOCK_TIMEOUT` config setting is never consumed:**
- Issue: `FANTASY_INGEST_LOCK_TIMEOUT` (default 300) is declared in `backend/src/fantasy/config.py` but never referenced outside the config class. The ingest lock check in `ingest_service.py` uses a raw `SELECT COUNT(*)` without any timeout enforcement.
- Impact: Stale `running` rows from crashed ingests will block re-ingestion indefinitely.
- Fix approach: In `IngestService.run()`, query `started_at` and skip/reset rows older than `INGEST_LOCK_TIMEOUT` seconds before raising the "already running" error.

**`get_scorecard` silently triggers a full `compute_league` on cache miss:**
- Issue: `IntelligenceService.get_scorecard()` in `backend/src/fantasy/intelligence/intelligence_service.py` (line 50) calls `self.compute_league(league_id)` when no scorecard row is found. This is a read endpoint (`GET /intelligence/scorecard/{league_id}/{roster_id}`) but uses a write connection via `get_read_db_conn` — or worse, silently fails on read-only connections.
- Impact: Unexpected compute triggered from a read path; race conditions if multiple read requests fire simultaneously for an un-computed league.
- Fix approach: Return 404 instead of auto-computing, or add an explicit check that the connection is writable.

**Duplicate `_loads`, `_ordinal`, `SCORECARD_FIELDS`, `WEAKNESS_LABELS` across modules:**
- Issue: The `_loads()` JSON helper is duplicated in at least 9 files (`dashboard.py`, `snapshot_service.py`, `trade_repo.py`, `pick_repo.py`, `profiling_engine.py`, `profiling_repo.py`, `rookie_repo.py`, `ingest_service.py`, `scorecard_engine.py`). `SCORECARD_FIELDS` and `WEAKNESS_LABELS` are duplicated between `dashboard.py` and `snapshot_service.py`. `_ordinal()` is duplicated between `dashboard.py` and `pick_engine.py`.
- Impact: Bug fixes or changes must be applied in multiple places.
- Fix approach: Extract `_loads` to `fantasy/utils.py`, import `SCORECARD_FIELDS`/`WEAKNESS_LABELS` from `intelligence/constants.py`.

**`Math.random()` used for client-side trade IDs in frontend:**
- Issue: Third-party trade session keys are generated via `Math.random().toString(36).slice(2, 10)` in `frontend/src/routes/trades.tsx` (line 45).
- Impact: Non-cryptographic, can collide in rapid succession. Low practical risk given small count, but fragile if extended.
- Fix approach: Use `crypto.randomUUID()` which is available in all modern browsers.

---

## Performance Bottlenecks

**No snapshot table pruning — unbounded growth:**
- Problem: Every ingest run appends one full or delta snapshot per league to `league_snapshots`. There is no DELETE, retention limit, or expiration logic anywhere in `backend/src/fantasy/snapshots/snapshot_service.py`.
- Impact: Over months of daily use with multiple leagues, `league_snapshots.payload_json` (which stores full roster+player-value JSON blobs) will grow substantially and slow queries that scan it (`_snapshot_pair_payloads`, `_build_risers_fallers`, `_load_previous_state`).
- Improvement path: Prune snapshots older than N days on each write, or keep only the last N full snapshots per league plus their associated deltas.

**`ingest_runs` and `transactions` tables have no retention policy:**
- Problem: Every ingest adds a row to `ingest_runs`. Every week of transactions adds rows permanently. Neither table is ever pruned.
- Impact: Minimal at current scale (single user, handful of leagues), but becomes a concern over multiple seasons.
- Improvement path: Archive or delete `ingest_runs` rows older than 90 days; no action needed for transactions as they are queryable by league.

**`dashboard/summaries` endpoint issues N+1 queries per league:**
- Problem: `GET /dashboard/summaries` iterates over all leagues and for each one fires multiple separate queries: `_user_roster_for_league`, `team_directions`, `team_scorecards`, `_top_exploit_window`, `_latest_snapshot_at`, `_latest_ingest_at`.
- Impact: For a user with 5 leagues this is ~30 queries per page load.
- Files: `backend/src/fantasy/routers/dashboard.py` (lines 695–756)
- Improvement path: Batch with CTEs or window functions to fetch all leagues in 1–2 queries.

**`compute_league` is fully synchronous and blocks the request thread:**
- Problem: `POST /intelligence/compute/{league_id}` runs all scorecard/direction/valuation computation synchronously on the FastAPI request thread. This is a CPU-heavy operation that blocks for multiple seconds on a full league.
- Files: `backend/src/fantasy/routers/intelligence.py`, `backend/src/fantasy/intelligence/intelligence_service.py`
- Improvement path: Background task (FastAPI `BackgroundTasks`) or async task queue.

---

## Fragile Areas

**`rookie_engine.py` heavy use of `# type: ignore` suppression:**
- Files: `backend/src/fantasy/rookie/rookie_engine.py` (8 suppressions at lines 99–320)
- Why fragile: The scored_rows list is typed as `list[dict]` but values are mutated to `RookiePlayer` objects mid-loop, causing mypy to lose track of types. Sorting and tier assignment both access `.composite_score` and `.full_name` through `type: ignore`, meaning type errors in `RookiePlayer` will not be caught at static analysis.
- Safe modification: Introduce a typed `ScoredRow` TypedDict or dataclass to carry both the raw dict fields and the `RookiePlayer`.
- Test coverage: `backend/tests/rookie/test_rookie_engine.py` covers happy-path scenarios but uses a fake repo that does not reflect real DB behavior.

**`startup_tasks.py` ALTER TABLE uses f-string with internal dict values:**
- Files: `backend/src/fantasy/startup_tasks.py` (line 76)
- Why fragile: `f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"` interpolates values from `_SCHEMA_COMPAT_COLUMNS`. If that dict is ever extended incorrectly, it would execute arbitrary DDL.
- Safe modification: Validate `table_name`, `column_name`, and `column_type` against allowlists before executing.

**Pick engine silently swallows all exceptions in `_load_class_strength_signal`:**
- Files: `backend/src/fantasy/picks/pick_engine.py` (lines 169–174)
- Why fragile: A bare `except Exception: return 0.0` means any failure in `RookieEngine.compute_class_strength` (including DB schema mismatches for the `rookie_board_cache` table, which is new) is silently ignored. Pick values will be computed with `class_strength_signal=0.0` without any warning.
- Safe modification: Log the exception before returning the fallback.

**Trade engine silently swallows all exceptions in `_build_pick_proxy`:**
- Files: `backend/src/fantasy/trade/trade_engine.py` (lines 52–79)
- Why fragile: A bare `except Exception: pass` means any failure in `get_pick_value` silently falls back to the static `PICK_MARKET_VALUES` proxy. No log or metric is emitted.
- Safe modification: Log the exception at WARNING level before falling through to the fallback.

**`ingest_service._backfill_roster_players` silently swallows fetch_players failure:**
- Files: `backend/src/fantasy/ingestion/ingest_service.py` (lines 107–110)
- Why fragile: `except Exception: player_catalog = {}` means a Sleeper API failure during player backfill results in all missing players being stored with only their player_id as their full_name. This has downstream effects on valuation and display.
- Safe modification: Log the exception so the gap is visible in ingest run logs.

---

## Test Coverage Gaps

**No tests for `ensure_runtime_schema` columns added via `ALTER TABLE`:**
- What's not tested: Whether the schema compat migration in `startup_tasks.py` correctly handles pre-existing databases missing the new columns.
- Files: `backend/src/fantasy/startup_tasks.py`
- Risk: A user upgrading from an older DB version could silently fail if the `ALTER TABLE` path has a bug.
- Priority: Medium

**No integration test for the ingest lock / concurrent ingest guard:**
- What's not tested: The `status = 'running'` check in `IngestService.run()` is tested in isolation but there is no test verifying that a stale `running` record from a crashed process permanently blocks re-ingestion.
- Files: `backend/src/fantasy/ingestion/ingest_service.py`, `backend/tests/test_ingest_service.py`
- Risk: Real-world crashes could permanently disable ingest for a league silently.
- Priority: High

**No tests for `dashboard/summaries` N+1 query behavior or ordering correctness:**
- What's not tested: The aggregation logic across multiple leagues in `_portfolio_owner_selection`, `_user_roster_for_league`, and the summary loop.
- Files: `backend/src/fantasy/routers/dashboard.py`, `backend/tests/test_dashboard_router.py`
- Risk: Portfolio owner detection could silently assign the wrong roster.
- Priority: Medium

**Rookie board and draft room router tests are present but thin:**
- What's not tested: Edge cases like leagues with zero available rookies, ties in composite scoring, or `compute_board` being called on a read-only connection.
- Files: `backend/tests/rookie/test_rookie_engine.py`, `backend/tests/test_rookie_board_router.py`, `backend/tests/test_draft_room_router.py`
- Priority: Low

---

## Scaling Limits

**DuckDB single-writer constraint:**
- Current capacity: One write connection at a time. DuckDB does not support concurrent writers.
- Limit: Two simultaneous ingest or compute requests to the same DB file will either fail or corrupt if write connections overlap.
- Current mitigation: The ingest lock guard (`status = 'running'`) prevents concurrent ingests for the same league but not for different leagues. Two leagues being ingested simultaneously would open two write connections.
- Scaling path: Serialize all write operations through a single connection pool or asyncio lock per DB path.

**Single-user `PORTFOLIO_OWNER_ID` design:**
- Current capacity: The entire dashboard is architected around a single configured owner ID. Multi-user would require per-request user context.
- Limit: Not multi-tenant by design.
- Scaling path: Requires architectural change; not a near-term concern for personal use.

---

## Dependencies at Risk

**`nfl_data_py` is not pinned tightly and has no fallback:**
- Risk: `nfl_data_py` is an unofficial community library that wraps nflverse data. Its data format has changed between seasons. If the column names or schema change, `nfl_data_loader.py` will fail silently or raise unhandled errors.
- Files: `backend/src/fantasy/ingestion/nfl_data_loader.py`
- Impact: Player stats weekly data gaps; pick valuation class strength silently defaults to 0.
- Migration plan: Pin to a specific version in `pyproject.toml` and add a schema validation step after load.

**Sleeper API is the sole external data source with no fallback:**
- Risk: All league data, roster data, and player catalogs come from `api.sleeper.app/v1`. If the API changes its schema or becomes unavailable, the entire ingestion pipeline fails.
- Impact: Stale data; no fallback mock or cached response.
- Migration plan: Not feasible to replace easily; ensure retry logic (already present via `tenacity`) is sufficient and surface failures clearly in the UI.

---

## Missing Critical Features

**No database backup or export mechanism:**
- Problem: `data/fantasy.duckdb` is a single binary file with no automated backup.
- Blocks: Any accidental deletion or corruption of the file loses all ingested data, computed intelligence, and manager profiles permanently.

**No migration runner at startup:**
- Problem: Alembic migrations (001–010) must be run manually with `alembic upgrade head`. New tables added by migrations (e.g., `pick_values`, `rookie_board_cache`) are not automatically created when the app starts with a fresh or partially-migrated database.
- Blocks: New users and phase deployments require manual CLI step that is not documented in the primary startup flow.

---

*Concerns audit: 2026-03-22*
