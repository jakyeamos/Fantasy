# Phase 1: Sleeper Ingestion - Research

**Researched:** 2026-03-12
**Domain:** Sleeper API ingestion, nfl_data_py, DuckDB, FastAPI, Alembic, Pydantic v2
**Confidence:** MEDIUM-HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Storage Backend**
- SQLite as the database — local file, zero setup, fits a single-user personal tool
- Alembic for schema migrations — schema changes must be versioned and reversible
- Database file lives in the project `data/` directory
- All leagues stored in shared tables with a `league_id` column — no per-league schema isolation

> **Research note:** STATE.md records a later override: DuckDB was chosen over SQLite (10-17x faster for analytical query patterns). All DDL must target DuckDB 1.5.0, not SQLite. Research reflects DuckDB throughout. The CONTEXT.md language retains "SQLite" but STATE.md supersedes it — treat DuckDB as the locked decision.

**Ingest Trigger**
- On-demand only — user triggers a refresh; no background scheduler in Phase 1
- Expected refresh cadence: daily or less
- Incremental ingest from the start — track state via timestamps/cursors and only fetch changes
- App is locked during ingest — reads are unavailable while an ingest run is in progress

**Scoring History**
- Use nfl_data_py (not Sleeper's deprecated player stats endpoint) for historical player-level stats
- Ingest all available seasons from nfl_data_py (10+ years) — seeds Phase 8's Historical Prospect Lab
- Reconstruct fantasy points from raw stat lines using each league's actual scoring settings
- Also ingest points for/against from Sleeper's standings endpoint (team-level PF/PA)

**Global Asset Baseline**
- Seeded from two sources: ADP signals (Sleeper ADP or public dynasty ADP source) + nfl_data_py scoring reconstruction
- Baseline is foundation-only in Phase 1 — Phase 2 applies adjustments on top

**Health Check & Gap Surfacing**
- Any data gap shown as an explicit named label with explanation and estimated resolution phase
- Format: "[Gap name]: [Why it's missing]. Expected resolution: Phase X."
- Silent data drops are not acceptable

### Claude's Discretion

- Manual correction model: how user overrides persist and survive re-ingestion (override table vs. correction log, conflict resolution strategy)
- Exact Alembic migration naming conventions and folder structure
- nfl_data_py data refresh cadence relative to Sleeper ingest cadence
- Stack scaffold structure (Python package layout, FastAPI vs Flask, monorepo vs separate backend/frontend dirs)

### Deferred Ideas (OUT OF SCOPE)

- None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INGEST-01 | Connect a Sleeper league by league ID and ingest all format settings (scoring system, roster positions, lineup slots, superflex/TEP/premium flags, bench/IR/taxi size) | Sleeper `GET /v1/league/<league_id>` returns `settings`, `scoring_settings`, `roster_positions` objects; all flag detection derived from these |
| INGEST-02 | Ingest current rosters for all teams including bench, IR, and taxi squad players | Sleeper `GET /v1/league/<league_id>/rosters` returns `starters`, `players`, `reserve` arrays per roster |
| INGEST-03 | Ingest current standings, points for, points against, and win/loss records per team | `roster.settings` contains fpts, fpts_decimal, wins, losses, ties; also available via matchups aggregate |
| INGEST-04 | Ingest all future rookie picks by team, year, and round | Sleeper `GET /v1/league/<league_id>/traded_picks` returns season/round/owner_id/roster_id for all traded picks |
| INGEST-05 | Ingest full trade history including all assets exchanged, timestamps, and participants | Sleeper `GET /v1/league/<league_id>/transactions/<week>` — must iterate all weeks; trade type returns `adds`, `drops`, `draft_picks` arrays |
| INGEST-06 | Ingest transaction history (adds, drops, waivers) for all managers | Same transactions endpoint as INGEST-05 — filter by `type` field (free_agent, waiver, trade) |
| INGEST-07 | User can manually correct any ingested data point | Override table pattern — corrections stored with `league_id`, `entity_type`, `entity_id`, `field`, `corrected_value`, `created_at`; applied as post-ingest layer |
| INGEST-08 | Display data freshness status and ingestion health per league with explicit gaps surfaced | IngestRun table tracks last_run_at, status, gaps (JSON); API endpoint exposes health per league |
</phase_requirements>

---

## Summary

Phase 1 is a pure data-plumbing phase: fetch from two sources (Sleeper REST API + nfl_data_py), persist to DuckDB, expose via FastAPI, and surface gaps explicitly. No analysis happens here.

The Sleeper API is a free, unauthenticated read-only HTTP REST API. The full set of endpoints needed for INGEST-01 through INGEST-06 are available and undeprecated. The one known deprecation — the `/stats/nfl/player/<season>/<week>` endpoint — was the player-level weekly stats feed. The decision to use nfl_data_py for historical stat reconstruction sidesteps this cleanly. nfl_data_py 0.3.3 provides `import_weekly_data()` with raw stat columns (receiving yards, receptions, targets, rushing yards, TDs, etc.) going back to 1999, which is sufficient for per-league fantasy point reconstruction.

DuckDB is the locked storage backend. Its Python DB-API is compatible with the standard `duckdb` package. Schema migrations via Alembic require registering a custom dialect implementation (`AlembicDuckDBImpl`) since Alembic does not natively ship a DuckDB dialect; the `duckdb-engine` SQLAlchemy driver (v0.17.0, March 2025) handles this. DuckDB enforces single-writer access — concurrent writes from multiple processes are not supported, which is acceptable here because ingest is on-demand and the app is locked during runs.

**Primary recommendation:** Build a `SleeperClient` (httpx AsyncClient + retry) that fetches raw JSON, a `SleeperMapper` that converts to Pydantic domain models, a `NflDataPyLoader` that pulls nfl_data_py weekly data, a `DuckDBRepository` that upserts via `INSERT OR REPLACE`, and a thin FastAPI layer that orchestrates ingest runs and exposes health status. This sequence matches the adapter-first architecture locked in STATE.md.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| duckdb | 1.5.0 | Primary database (locked in STATE.md) | 10-17x faster than SQLite for analytical patterns; single-file local deployment |
| duckdb-engine | 0.17.0 | SQLAlchemy dialect for DuckDB | Required for Alembic integration; latest release March 2025 |
| alembic | 1.13.x | Schema migrations | Versioned, reversible DDL; locked decision |
| sqlalchemy | 2.0.x | ORM/Core for model definitions + Alembic autogenerate | Required by duckdb-engine; v2 async support |
| fastapi | 0.115.x | HTTP API layer | Locked in roadmap; async-native, Pydantic v2 native |
| pydantic | 2.x | Domain models and request/response validation | FastAPI dependency; v2 is 5-17x faster than v1 |
| httpx | 0.27.x | Async HTTP client for Sleeper API | Async-native; supports retry/backoff patterns |
| nfl_data_py | 0.3.3 | Historical NFL player stats (1999-present) | Only open-source library with full nflverse data in Python |
| uvicorn | 0.30.x | ASGI server for FastAPI | Standard FastAPI deployment |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tenacity | 8.x | Retry with exponential backoff + jitter | Wrapping httpx calls to Sleeper API for rate-limit resilience |
| polars | 1.x | DataFrame processing for nfl_data_py bulk loads | Locked in roadmap for analytical transforms; faster than pandas for bulk inserts |
| pytest | 8.x | Test framework | All unit/integration tests |
| pytest-asyncio | 0.23.x | Async test support | Required for testing async FastAPI endpoints and httpx calls |
| pytest-httpx | 0.30.x | Mock httpx responses in tests | Isolates Sleeper API tests from live network |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| duckdb-engine | duckdb-sqlalchemy (leonardovida fork) | Fork claims better production defaults but low adoption; duckdb-engine is the original and more referenced |
| httpx | aiohttp | httpx is simpler for one-off clients, matches FastAPI's async idiom; aiohttp requires more boilerplate |
| tenacity | httpx-retries | tenacity is more battle-tested; httpx-retries is newer but less documented |
| polars | pandas | polars is locked in roadmap; pandas is more familiar but 3-5x slower at this scale |

**Installation:**
```bash
pip install duckdb==1.5.0 duckdb-engine alembic "sqlalchemy>=2.0" "fastapi>=0.115" "pydantic>=2.0" httpx tenacity polars uvicorn pytest pytest-asyncio pytest-httpx
```

---

## Architecture Patterns

### Recommended Project Structure

```
fantasy/
├── backend/
│   ├── src/
│   │   └── fantasy/
│   │       ├── __init__.py
│   │       ├── main.py               # FastAPI app factory
│   │       ├── config.py             # Settings (Pydantic BaseSettings)
│   │       ├── db/
│   │       │   ├── __init__.py
│   │       │   ├── connection.py     # DuckDB engine + session factory
│   │       │   └── models.py         # SQLAlchemy ORM table definitions
│   │       ├── ingestion/
│   │       │   ├── __init__.py
│   │       │   ├── sleeper_client.py # httpx AsyncClient, all Sleeper API calls
│   │       │   ├── sleeper_mapper.py # Raw JSON → Pydantic domain models
│   │       │   ├── nfl_data_loader.py# nfl_data_py calls + polars transforms
│   │       │   ├── ingest_service.py # Orchestrates full ingest run
│   │       │   └── gap_detector.py   # Identifies and labels data gaps
│   │       ├── corrections/
│   │       │   ├── __init__.py
│   │       │   └── override_service.py # Manual correction CRUD + apply logic
│   │       ├── repositories/
│   │       │   ├── __init__.py
│   │       │   └── league_repo.py    # DuckDB read/upsert for all league tables
│   │       └── routers/
│   │           ├── __init__.py
│   │           ├── ingest.py         # POST /ingest/{league_id}, GET /ingest/status
│   │           ├── health.py         # GET /health/{league_id}
│   │           └── corrections.py    # CRUD /corrections
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── 001_initial_schema.py
│   ├── alembic.ini
│   └── pyproject.toml
├── data/
│   └── fantasy.duckdb               # Database file (gitignored)
└── .planning/
```

### Pattern 1: Adapter-first Isolation (locked in STATE.md)

**What:** All Sleeper JSON parsing is isolated in `SleeperMapper`. FastAPI routers, repositories, and services consume only internal Pydantic domain models — never raw API dicts.

**When to use:** Always. Every Sleeper API call produces a raw dict that immediately passes through `SleeperMapper` before touching any other layer.

**Example:**
```python
# sleeper_mapper.py
from pydantic import BaseModel
from typing import Optional

class LeagueSettings(BaseModel):
    league_id: str
    name: str
    season: str
    scoring_settings: dict[str, float]
    roster_positions: list[str]
    settings: dict          # raw settings blob preserved for flag extraction
    superflex: bool
    tep: bool               # tight end premium
    ppr: float              # 0, 0.5, or 1.0 derived from scoring_settings

class SleeperMapper:
    @staticmethod
    def map_league(raw: dict) -> LeagueSettings:
        scoring = raw.get("scoring_settings", {})
        return LeagueSettings(
            league_id=raw["league_id"],
            name=raw["name"],
            season=raw["season"],
            scoring_settings=scoring,
            roster_positions=raw.get("roster_positions", []),
            settings=raw.get("settings", {}),
            superflex="SUPER_FLEX" in raw.get("roster_positions", []),
            tep=scoring.get("bonus_rec_te", 0.0) > 0,
            ppr=scoring.get("rec", 0.0),
        )
```

### Pattern 2: Upsert via INSERT OR REPLACE in DuckDB

**What:** DuckDB supports `INSERT OR REPLACE INTO` (and `INSERT INTO ... ON CONFLICT DO UPDATE SET`) for idempotent ingest runs. Use `ON CONFLICT` syntax for partial updates.

**When to use:** All ingest operations — every table must be safe to re-run from scratch.

**Example:**
```python
# repositories/league_repo.py
import duckdb

def upsert_league(conn: duckdb.DuckDBPyConnection, league: LeagueSettings) -> None:
    conn.execute("""
        INSERT INTO leagues (league_id, name, season, scoring_settings, superflex, tep, ppr)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (league_id) DO UPDATE SET
            name = EXCLUDED.name,
            season = EXCLUDED.season,
            scoring_settings = EXCLUDED.scoring_settings,
            superflex = EXCLUDED.superflex,
            tep = EXCLUDED.tep,
            ppr = EXCLUDED.ppr
    """, [league.league_id, league.name, league.season,
          str(league.scoring_settings), league.superflex, league.tep, league.ppr])
```

### Pattern 3: Override Table for Manual Corrections (INGEST-07)

**What:** A dedicated `corrections` table stores user overrides keyed by `(league_id, entity_type, entity_id, field)`. After each ingest, the ingest service applies all active corrections on top of freshly ingested data. Corrections survive re-ingestion — the correction is never deleted by an ingest run.

**When to use:** Any user edit to an ingested value. The correction record is the source of truth; ingested data is the default.

**Example schema:**
```sql
CREATE TABLE IF NOT EXISTS corrections (
    id          INTEGER PRIMARY KEY,
    league_id   VARCHAR NOT NULL,
    entity_type VARCHAR NOT NULL,  -- 'player', 'pick', 'roster_slot', 'league_setting'
    entity_id   VARCHAR NOT NULL,
    field       VARCHAR NOT NULL,
    original_value VARCHAR,
    corrected_value VARCHAR NOT NULL,
    corrected_by VARCHAR DEFAULT 'user',
    created_at  TIMESTAMP DEFAULT current_timestamp,
    UNIQUE (league_id, entity_type, entity_id, field)
);
```

### Pattern 4: Incremental Ingest via IngestRun Cursor

**What:** An `ingest_runs` table records every run's start time, completion time, and a JSON cursor blob. On re-run, the service checks `last_completed_at` per data type and skips data whose upstream `updated_at` is older than the cursor.

**When to use:** All data types that have a Sleeper-provided `updated_at` or `created_at` timestamp. For transactions, the cursor tracks the highest-week fetched so far.

**Example schema:**
```sql
CREATE TABLE IF NOT EXISTS ingest_runs (
    id              INTEGER PRIMARY KEY,
    league_id       VARCHAR NOT NULL,
    run_type        VARCHAR NOT NULL,  -- 'full', 'incremental'
    status          VARCHAR NOT NULL,  -- 'running', 'complete', 'failed'
    started_at      TIMESTAMP NOT NULL DEFAULT current_timestamp,
    completed_at    TIMESTAMP,
    cursor_json     JSON,              -- type-specific state cursors
    gaps_json       JSON,              -- array of gap objects surfaced this run
    error_message   VARCHAR
);
```

### Pattern 5: Fantasy Point Reconstruction from nfl_data_py

**What:** `import_weekly_data(years)` returns raw stat columns per player per week. Fantasy points are reconstructed by multiplying each stat column by the league's corresponding scoring coefficient from `league.scoring_settings`.

**Why this works:** Sleeper's `scoring_settings` object is a dict of stat keys (e.g., `rec`, `pass_yd`, `rush_yd`, `bonus_rec_te`) mapped to point values. nfl_data_py's weekly columns map onto these same stat concepts (with a column name translation layer).

**Key nfl_data_py columns for reconstruction:**
- `receptions`, `targets`, `receiving_yards`, `receiving_tds` → receiver scoring
- `rushing_yards`, `rushing_tds`, `rushing_fumbles_lost` → rusher scoring
- `passing_yards`, `passing_tds`, `interceptions`, `passing_2pt_conversions` → QB scoring
- `fantasy_points`, `fantasy_points_ppr` → pre-computed baselines (sanity check only)

**Mapping layer required:** Sleeper key `rec` → nfl_data_py column `receptions`; `rush_yd` → `rushing_yards`; etc. This mapping is the core of `NflDataPyLoader.compute_fantasy_points(stats_df, scoring_settings)`.

### Anti-Patterns to Avoid

- **Fetching `/v1/players/nfl` on every ingest:** This is a 5MB payload. Cache it locally; Sleeper's docs say once per day at most. Store player metadata in a `players` table and refresh only on full ingest.
- **Fetching transactions without iterating all weeks:** The transactions endpoint is keyed by week number. For trade history, you must loop weeks 1–18 (regular season + playoffs). Missing any week creates silent gaps in trade history.
- **Reconstructing scoring without a stat-key mapping table:** Sleeper scoring keys do not match nfl_data_py column names. Without an explicit translation table, reconstruction silently drops stats.
- **Running Alembic autogenerate against DuckDB without registering AlembicDuckDBImpl:** Alembic raises an error without the dialect registration. Add it to `alembic/env.py` before the first migration.
- **Using SQLAlchemy SERIAL / auto-increment default for PKs:** DuckDB does not support PostgreSQL's SERIAL type. Use `SEQUENCE` or DuckDB's `INTEGER PRIMARY KEY` which auto-increments natively via `nextval`.
- **Opening a second write connection during ingest:** DuckDB enforces single-writer at the process level. If the FastAPI app keeps a read connection open and the ingest service opens a write connection, the second connection must be opened in a compatible mode or it will block/fail. Use read-only connections for the API layer during ingest.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP retry with backoff | Custom retry loop | `tenacity` with `retry_if_exception_type(httpx.HTTPError)` + exponential backoff + jitter | Retry storms, thundering herd, non-retriable vs. retriable status codes all handled |
| Schema migrations | Manual SQL ALTER TABLE scripts | Alembic with duckdb-engine dialect | Version ordering, rollback, autogenerate from SQLAlchemy models |
| JSON-to-domain mapping validation | Custom dict parsing with `dict.get()` chains | Pydantic v2 models in `SleeperMapper` | Missing fields, type coercion, nullable vs. required — silently wrong without validation |
| Bulk DataFrame-to-DuckDB inserts | `executemany()` row by row | `duckdb.execute("INSERT INTO t SELECT * FROM df")` with polars DataFrame | DuckDB can query polars DataFrames directly; executemany is documented as slow for bulk loads |
| Fantasy point formula engine | Custom weighted-sum parser | Explicit `scoring_settings` dict multiplication with a key-map translation | Sleeper has 50+ scoring keys; missing one causes silent undercounting |

**Key insight:** The Sleeper API is unauthenticated and simple; the complexity is in completeness (iterating all weeks for transactions), correctness (stat key translation for scoring reconstruction), and resilience (null/missing fields in API responses for inactive leagues).

---

## Common Pitfalls

### Pitfall 1: Transactions Endpoint Requires Per-Week Iteration

**What goes wrong:** Developer calls `GET /v1/league/{id}/transactions/1` and gets one week, assumes that's all trades.
**Why it happens:** The endpoint is week-scoped, not league-scoped. Dynasty leagues commonly have off-season trades in weeks 1-3 before the season and keeper trades in weeks 14-18.
**How to avoid:** Iterate weeks 1 through 18 (or current_week from `/v1/state/nfl` + buffer). Store the max-week-fetched in the ingest cursor so incremental runs only fetch new weeks.
**Warning signs:** Trade count in DB is suspiciously low relative to league age; trades from preseason missing.

### Pitfall 2: Sleeper Players Endpoint is 5MB — Don't Poll It

**What goes wrong:** Calling `/v1/players/nfl` on every ingest run adds 5-10 seconds per run and risks IP block.
**Why it happens:** It feels natural to refresh player metadata alongside roster data.
**How to avoid:** Fetch once at first ingest, store in `players` table. Add a separate "refresh player metadata" ingest run type that runs at most daily. Sleeper's docs explicitly recommend this.
**Warning signs:** Ingest times over 10 seconds; rate limit 429 responses.

### Pitfall 3: nfl_data_py Stat Key Translation Gaps

**What goes wrong:** Fantasy point reconstruction silently underestimates points because a Sleeper scoring key has no matching nfl_data_py column (or column name differs).
**Why it happens:** The two systems use different naming conventions. Example: Sleeper uses `rec_yd`, nfl_data_py uses `receiving_yards`.
**How to avoid:** Build an explicit `SLEEPER_TO_NFLDATA_STAT_MAP` dict in `NflDataPyLoader`. Log any Sleeper scoring key that has no map entry as a named gap in `gaps_json`. Test reconstruction against known Sleeper matchup totals for at least one season.
**Warning signs:** Reconstructed fantasy totals are consistently 10-20% below Sleeper matchup totals.

### Pitfall 4: DuckDB Single-Writer Constraint During Concurrent Access

**What goes wrong:** FastAPI serves read queries while an ingest run holds the write connection. Either reads block or the second connection raises `IOException: database file is locked`.
**Why it happens:** DuckDB file-based databases only allow one active write connection per file. Multiple readers are fine; mixing is not.
**How to avoid:** The locked-during-ingest policy (locked decision) handles this. Implement an `ingest_lock` flag in `IngestRun` — API endpoints return 503 with `"ingest_in_progress": true` when a run is active. Open read connections in `read_only=True` mode; open write connections only from the ingest service.
**Warning signs:** `IOException: Already opened database in READ_WRITE mode by another process`; hanging API requests during ingest.

### Pitfall 5: Alembic Autogenerate Silently Omits DuckDB-Specific Types

**What goes wrong:** Alembic's autogenerate compares SQLAlchemy model definitions to the live schema but may not correctly reflect DuckDB-native types (e.g., `JSON`, `HUGEINT`), leading to false-positive migrations or missed changes.
**Why it happens:** duckdb-engine is derived from the PostgreSQL dialect; some DuckDB types don't round-trip cleanly through SQLAlchemy reflection.
**How to avoid:** Review all autogenerated migration files before applying. Use `VARCHAR` / `TEXT` for JSON blobs initially (DuckDB stores them as strings anyway). Add `JSON` type only after verifying reflection works.
**Warning signs:** `alembic upgrade head` produces no error but schema diff shows unexpected changes on next autogenerate.

### Pitfall 6: traded_picks vs. Transactions for Pick Ownership

**What goes wrong:** Using only `/traded_picks` for current pick ownership misses picks that were traded and then returned (multi-step trades). Using only the transactions endpoint to reconstruct pick ownership is complex and error-prone.
**How to avoid:** Use `/traded_picks` as the authoritative current state of pick ownership (it shows the current `owner_id` for every traded pick). Use the transactions endpoint for trade history audit log. These serve different purposes — don't conflate them.
**Warning signs:** Pick ownership in DB disagrees with Sleeper UI.

---

## Code Examples

Verified patterns from official sources:

### DuckDB Python DB-API Connection (local file)
```python
# Source: https://duckdb.org/docs/stable/clients/python/dbapi
import duckdb

# Write connection (one at a time only)
write_conn = duckdb.connect("data/fantasy.duckdb")

# Read-only connections (multiple allowed)
read_conn = duckdb.connect("data/fantasy.duckdb", read_only=True)
```

### DuckDB Upsert Pattern
```python
# Source: https://duckdb.org/docs/stable/sql/statements/merge_into
conn.execute("""
    INSERT INTO leagues (league_id, name, season)
    VALUES (?, ?, ?)
    ON CONFLICT (league_id) DO UPDATE SET
        name = EXCLUDED.name,
        season = EXCLUDED.season
""", [league_id, name, season])
```

### Alembic DuckDB Dialect Registration
```python
# Source: https://github.com/Mause/duckdb_engine
# Must be loaded before any Alembic operations — add to alembic/env.py
from alembic.ddl.impl import DefaultImpl

class AlembicDuckDBImpl(DefaultImpl):
    """Alembic implementation for DuckDB."""
    __dialect__ = "duckdb"

# alembic.ini sqlalchemy.url:
# sqlalchemy.url = duckdb:///data/fantasy.duckdb
```

### Sleeper API — Fetch All Transactions Across All Weeks
```python
# Source: https://docs.sleeper.com/
import httpx
import asyncio

async def fetch_all_transactions(league_id: str, max_week: int = 18) -> list[dict]:
    """Iterate all weeks to build complete trade/transaction history."""
    all_transactions = []
    async with httpx.AsyncClient() as client:
        for week in range(1, max_week + 1):
            resp = await client.get(
                f"https://api.sleeper.app/v1/league/{league_id}/transactions/{week}"
            )
            resp.raise_for_status()
            all_transactions.extend(resp.json())
    return all_transactions
```

### nfl_data_py — Weekly Stats Import
```python
# Source: https://pypi.org/project/nfl-data-py/
import nfl_data_py as nfl

# Import all available seasons (1999-present)
years = list(range(1999, 2026))
weekly = nfl.import_weekly_data(years)
# Returns DataFrame with columns including:
# player_id, player_name, position, week, season,
# receptions, targets, receiving_yards, receiving_tds,
# rushing_yards, rushing_tds,
# passing_yards, passing_tds, interceptions,
# fantasy_points, fantasy_points_ppr
```

### Fantasy Point Reconstruction
```python
# Pattern: apply league scoring_settings to nfl_data_py stat columns

SLEEPER_TO_NFLDATA_MAP = {
    "rec":           "receptions",
    "rec_yd":        "receiving_yards",
    "rec_td":        "receiving_tds",
    "rush_yd":       "rushing_yards",
    "rush_td":       "rushing_tds",
    "pass_yd":       "passing_yards",
    "pass_td":       "passing_tds",
    "pass_int":      "interceptions",
    "bonus_rec_te":  "receptions",      # TEP: receptions x bonus for TEs only
    # Add remaining keys as discovered
}

def reconstruct_fantasy_points(stats_row: dict, scoring_settings: dict, position: str) -> float:
    total = 0.0
    for sleeper_key, points_per_unit in scoring_settings.items():
        nfldata_col = SLEEPER_TO_NFLDATA_MAP.get(sleeper_key)
        if nfldata_col is None:
            continue  # Log as gap
        stat_value = stats_row.get(nfldata_col, 0.0) or 0.0
        # TEP applies only to TEs
        if sleeper_key == "bonus_rec_te" and position != "TE":
            continue
        total += stat_value * points_per_unit
    return round(total, 2)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Sleeper `/stats/nfl/player` for historical stats | nfl_data_py for historical, matchups endpoint for current season | ~2023 | Must reconstruct from raw stats; nfl_data_py is the correct path |
| SQLite for local analytics tools | DuckDB for local analytics tools | 2022-2023 | 10-17x query speed on analytical workloads; `INSERT OR REPLACE` upsert parity |
| Pydantic v1 | Pydantic v2 (2023+) | 2023 | 5-50x validation performance; breaking API changes (validators, model_dump) |
| requests + urllib | httpx (async-native) | 2021+ | Async-first; matches FastAPI's async idiom |

**Deprecated/outdated:**
- Sleeper `/stats/nfl/player/<season_type>/<season>/<week>` endpoint: removed from public API. Do not use. nfl_data_py is the replacement path for historical stats.
- `sleeper-api-wrapper` PyPI package: last updated 2021, lacks dynasty-specific endpoints. Do not use; write a direct httpx client instead.
- Pydantic v1 `.dict()` / `.parse_obj()`: replaced by `.model_dump()` / `Model.model_validate()` in v2. Using v1 APIs against v2 raises deprecation warnings.

---

## Open Questions

1. **Sleeper scoring_settings key completeness**
   - What we know: Sleeper returns a `scoring_settings` dict with 20-50+ keys depending on league configuration (TEP, superflex, kick return TDs, etc.)
   - What's unclear: The full enumeration of all possible Sleeper scoring keys and their nfl_data_py column equivalents is not in any single authoritative source
   - Recommendation: During Wave 0, call `GET /v1/league/{id}` against at least two real leagues, inspect the full `scoring_settings` dict, and build the `SLEEPER_TO_NFLDATA_MAP` from that data. Flag unmapped keys as named gaps immediately.

2. **taxi squad field in roster response**
   - What we know: The rosters endpoint returns `starters`, `players`, `reserve` arrays
   - What's unclear: Whether taxi squad players appear in a dedicated `taxi` array or are mixed into `reserve`. The official docs do not explicitly label this.
   - Recommendation: Inspect a live dynasty league roster response to confirm. If taxi is in `reserve`, the IR vs. taxi distinction requires a separate slot-type inference from league settings.

3. **nfl_data_py 2025 season availability**
   - What we know: The library is updated through the most recently completed season; 0.3.3 released September 2024
   - What's unclear: Whether 2025 season data is fully loaded into nflverse and reflected in nfl_data_py as of March 2026
   - Recommendation: At implementation time, call `nfl.import_weekly_data([2025])` and verify row count. If empty, surface as a named gap: "2025 season stats not yet available in nfl_data_py. Expected resolution: Phase 1 re-ingest after nflverse update."

4. **ADP source for Global Asset Baseline**
   - What we know: Sleeper does not expose a documented ADP endpoint in its public API. Third-party sites (BeatADP, FantasyPros, DraftSharks) publish Sleeper-derived ADP data.
   - What's unclear: Whether any of these sources have a machine-readable API or require scraping
   - Recommendation: For Phase 1 baseline seeding, use FantasyPros dynasty ADP via their free CSV export (or scrape if no API). The baseline is refined in Phase 2 — imprecision is acceptable in Phase 1.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.23.x |
| Config file | `backend/pyproject.toml` — does not exist yet (Wave 0) |
| Quick run command | `pytest backend/tests/ -x -q` |
| Full suite command | `pytest backend/tests/ -v --tb=short` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INGEST-01 | League settings ingested correctly (scoring, positions, flags) | unit | `pytest backend/tests/test_sleeper_mapper.py::test_map_league_settings -x` | Wave 0 |
| INGEST-01 | superflex/TEP/ppr flags derived correctly | unit | `pytest backend/tests/test_sleeper_mapper.py::test_flag_derivation -x` | Wave 0 |
| INGEST-02 | Roster players ingested, starters/bench/IR/taxi slots correct | unit | `pytest backend/tests/test_sleeper_mapper.py::test_map_roster -x` | Wave 0 |
| INGEST-03 | Standings PF/PA/W/L ingested from roster settings | unit | `pytest backend/tests/test_league_repo.py::test_upsert_standings -x` | Wave 0 |
| INGEST-04 | Traded picks current ownership ingested | unit | `pytest backend/tests/test_sleeper_mapper.py::test_map_traded_picks -x` | Wave 0 |
| INGEST-05 | Full trade history across all weeks ingested | integration | `pytest backend/tests/test_ingest_service.py::test_trade_history_all_weeks -x` | Wave 0 |
| INGEST-06 | Transactions (adds, drops, waivers) ingested | integration | `pytest backend/tests/test_ingest_service.py::test_transactions_by_type -x` | Wave 0 |
| INGEST-07 | Manual correction persists after re-ingest | integration | `pytest backend/tests/test_corrections.py::test_correction_survives_reingest -x` | Wave 0 |
| INGEST-08 | Data freshness status and gaps surfaced per league | unit | `pytest backend/tests/test_gap_detector.py::test_gap_surfacing -x` | Wave 0 |
| All | Ingest is idempotent — running twice produces same result | integration | `pytest backend/tests/test_ingest_service.py::test_idempotent_ingest -x` | Wave 0 |
| All | Null/missing Sleeper API fields do not crash ingest | unit | `pytest backend/tests/test_sleeper_mapper.py::test_partial_response_handling -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest backend/tests/ -x -q -k "not integration"`
- **Per wave merge:** `pytest backend/tests/ -v --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `backend/pyproject.toml` — pytest config, dependencies, `[tool.pytest.ini_options]` asyncio_mode = "auto"
- [ ] `backend/tests/__init__.py` — package marker
- [ ] `backend/tests/conftest.py` — shared fixtures: in-memory DuckDB connection, mock Sleeper API responses via pytest-httpx
- [ ] `backend/tests/test_sleeper_mapper.py` — covers INGEST-01, INGEST-02, INGEST-04; null-handling
- [ ] `backend/tests/test_league_repo.py` — covers INGEST-03; upsert idempotency
- [ ] `backend/tests/test_ingest_service.py` — covers INGEST-05, INGEST-06; full run integration
- [ ] `backend/tests/test_corrections.py` — covers INGEST-07
- [ ] `backend/tests/test_gap_detector.py` — covers INGEST-08
- [ ] Framework install: `pip install pytest pytest-asyncio pytest-httpx`

---

## Sources

### Primary (HIGH confidence)
- https://docs.sleeper.com/ — All Sleeper API endpoints, rate limits, response structures
- https://pypi.org/project/nfl-data-py/ — nfl_data_py 0.3.3 functions, year ranges, install
- https://duckdb.org/docs/stable/clients/python/dbapi — DuckDB Python DB-API, connection modes, concurrency
- https://duckdb.org/docs/stable/sql/statements/merge_into — DuckDB upsert via MERGE INTO / ON CONFLICT
- https://github.com/Mause/duckdb_engine — duckdb-engine v0.17.0 (March 2025), Alembic dialect registration, known limitations

### Secondary (MEDIUM confidence)
- https://github.com/nflverse/nfl_data_py — import_weekly_data columns, historical season range (1999-present)
- https://duckdb.org/docs/stable/connect/concurrency — DuckDB single-writer constraint, WAL mode, read-only connections
- https://motherduck.com/docs/integrations/language-apis-and-drivers/python/sqlalchemy/ — DuckDB SQLAlchemy connection string format

### Tertiary (LOW confidence — flag for validation)
- nfl_data_py column name list (receptions, receiving_yards etc.) — inferred from multiple community examples; verify with `nfl.see_weekly_cols()` at implementation time
- Sleeper `taxi` array in roster response — not confirmed from official docs; requires live API inspection

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified via PyPI and official docs; versions confirmed
- Architecture: MEDIUM — patterns derived from official docs + community sources; greenfield, no prior codebase to validate against
- Pitfalls: MEDIUM-HIGH — most pitfalls verified via official DuckDB/Sleeper docs; stat key translation gap is LOW confidence until mapping is built

**Research date:** 2026-03-12
**Valid until:** 2026-04-12 (stable ecosystem — duckdb-engine, nfl_data_py, and Sleeper API are not fast-moving)
