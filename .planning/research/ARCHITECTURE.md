# Architecture Research

**Domain:** Dynasty fantasy football intelligence system — multi-engine analytics platform
**Researched:** 2026-03-11
**Confidence:** HIGH (platform specifics), MEDIUM (schema patterns), HIGH (engine decoupling)

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          REACT FRONTEND                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ League   │  │ Team     │  │  Trade   │  │  Prospect /      │   │
│  │ Cards    │  │ Dossier  │  │  Workbench│  │  Pick Engine     │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘   │
│       │             │             │                  │              │
│  ┌────┴─────────────┴─────────────┴──────────────────┴──────────┐  │
│  │                TanStack Query (server-state cache)             │  │
│  └───────────────────────────────┬────────────────────────────────┘  │
└──────────────────────────────────┼──────────────────────────────────┘
                                   │ HTTP REST (JSON)
┌──────────────────────────────────┼──────────────────────────────────┐
│                         FASTAPI BACKEND                              │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                       API Router Layer                          │  │
│  │  /leagues  /teams  /trades  /prospects  /picks  /managers  /sync│  │
│  └───────────────────────────────┬────────────────────────────────┘  │
│                                  │                                   │
│  ┌───────────────────────────────┼────────────────────────────────┐  │
│  │                   ENGINE ORCHESTRATOR                           │  │
│  │  Accepts enriched domain models. Decides which engines to run.  │  │
│  │  Composes partial scores into full recommendations.             │  │
│  └──┬──────────┬──────────┬──────────┬──────────┬──────────┬──────┘  │
│     │          │          │          │          │          │         │
│  ┌──┴──┐  ┌───┴──┐  ┌───┴──┐  ┌───┴──┐  ┌───┴──┐  ┌───┴──┐      │
│  │ E1  │  │ E2   │  │ E3   │  │ E4   │  │ E5   │  │ E6   │      │
│  │Glob.│  │Leag. │  │Team  │  │Mgr.  │  │Trade │  │Prosp.│      │
│  │Base │  │Ctx   │  │Dir.  │  │Behav.│  │Path  │  │Res.  │      │
│  └──┬──┘  └───┬──┘  └───┬──┘  └───┬──┘  └───┬──┘  └───┬──┘      │
│     │         │          │         │          │         │          │
│  ┌──┴─────────┴──────────┴─────────┴──────────┴─────────┴───────┐  │
│  │                     DOMAIN MODEL LAYER                         │  │
│  │        Pydantic models — platform-agnostic typed structs        │  │
│  └───────────────────────────────┬────────────────────────────────┘  │
│                                  │                                   │
│  ┌───────────────────────────────┼────────────────────────────────┐  │
│  │                   PLATFORM ADAPTER LAYER                        │  │
│  │        SleeperAdapter  |  (future: ESPNAdapter, etc.)           │  │
│  │  Translates raw API responses → domain models. No analysis here.│  │
│  └───────────────────────────────┬────────────────────────────────┘  │
│                                  │                                   │
│  ┌───────────────────────────────┼────────────────────────────────┐  │
│  │             SYNC SCHEDULER (APScheduler)                        │  │
│  │   Triggers: startup, manual, timed refresh (configurable).      │  │
│  │   Calls SleeperAdapter → writes domain models → persists.       │  │
│  └───────────────────────────────┬────────────────────────────────┘  │
└──────────────────────────────────┼──────────────────────────────────┘
                                   │
┌──────────────────────────────────┼──────────────────────────────────┐
│                         DATA LAYER (SQLite)                          │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌─────────────────┐  │
│  │  Platform │  │  League / │  │  Analysis │  │   Prospect /    │  │
│  │  Raw Cache│  │  Roster   │  │  Results  │  │   Historical    │  │
│  └───────────┘  └───────────┘  └───────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                         Sleeper Public API
                         (read-only, no auth)
```

### Component Responsibilities

| Component | Responsibility | Notes |
|-----------|----------------|-------|
| React UI | Render recommendations, accept manual overrides, navigate between leagues | Vite + TanStack Query for server-state cache; no business logic |
| FastAPI Router | HTTP boundary — accepts requests, validates input, delegates to orchestrator | Thin layer; no analysis logic |
| Engine Orchestrator | Decides which engines run for a given request, composes partial scores, returns full recommendation | Central dependency resolution point |
| E1: Global Asset Baseline | Global player valuation, format-adjusted value curves, age-risk curves, position scarcity | Platform-agnostic; uses historical + current player data |
| E2: League Context Engine | Normalizes league settings (scoring, roster config, superflex, TEP flags) into a format-context object consumed by all other engines | Run first — other engines depend on its output |
| E3: Team Direction Engine | Generates scorecard sub-scores (win-now, future value, depth, pick capital, flexibility, fragility, age risk, liquidity, positional insulation), detects primary direction with confidence, alternate viable directions | Depends on E1 and E2 |
| E4: Manager Behavior Engine | Builds dossier per manager: trade tendencies, overpay patterns, exploitability score, pitch angles | Depends on transaction history; degrades gracefully when data is sparse |
| E5: Trade Pathing Engine | Evaluates trade proposals (market fairness, roster fit, direction fit, timing), surfaces reroutes, package alternatives, pitch notes, opening offers per manager | Depends on E1, E2, E3, E4 |
| E6: Prospect Research Engine | Format-aware rookie board, draft capital models, archetype clustering, historical comps, hit-rate buckets, pick timing recommendations | Depends on E1, E2; E4 optional overlay for draft tendencies |
| Platform Adapter Layer | Translates raw Sleeper JSON into domain models. Handles API quirks, missing fields, and partial data. No analysis. | Swap or add adapters without touching engines |
| Domain Model Layer | Pydantic typed structs: Player, League, Roster, Pick, Trade, Manager, Snapshot. These are what engines consume and produce — never raw API payloads. | Single source of truth for data contracts |
| Sync Scheduler | APScheduler within FastAPI process. Triggers data refresh from Sleeper. Writes to DB. Marks cache stale for downstream. | Configurable: startup sync, interval sync, manual trigger |
| SQLite | Persistent storage — raw cache, normalized league data, analysis results, snapshots, prospect historical database | SQLAlchemy ORM; single file for local deployment |

## Recommended Project Structure

```
fantasy/
├── backend/
│   ├── main.py                     # FastAPI app entrypoint, lifespan, scheduler mount
│   ├── api/
│   │   ├── routes/
│   │   │   ├── leagues.py          # /leagues endpoints
│   │   │   ├── teams.py            # /teams, /scorecard
│   │   │   ├── trades.py           # /trades, /trade-path
│   │   │   ├── picks.py            # /picks, /pick-valuation
│   │   │   ├── managers.py         # /managers, /dossier
│   │   │   ├── prospects.py        # /prospects, /rookie-board
│   │   │   └── sync.py             # /sync (manual trigger)
│   │   └── dependencies.py         # Shared FastAPI dependency injection
│   ├── adapters/
│   │   ├── base.py                 # AbstractPlatformAdapter protocol
│   │   ├── sleeper/
│   │   │   ├── client.py           # Raw HTTP calls to Sleeper API
│   │   │   ├── mapper.py           # Sleeper JSON → domain models
│   │   │   └── endpoints.py        # Sleeper URL constants
│   │   └── (espn/ or yahoo/ later) # Future adapter slots
│   ├── domain/
│   │   ├── models.py               # Pydantic: Player, League, Roster, Pick, Trade, etc.
│   │   └── enums.py                # TeamDirection, ConfidenceLevel, ScoringFormat, etc.
│   ├── engines/
│   │   ├── orchestrator.py         # Coordinates engine execution order, composes output
│   │   ├── e1_global_baseline.py   # Global asset valuation
│   │   ├── e2_league_context.py    # League settings normalization
│   │   ├── e3_team_direction.py    # Team scorecard, direction detection
│   │   ├── e4_manager_behavior.py  # Manager dossier and profiling
│   │   ├── e5_trade_pathing.py     # Trade evaluation, pathing, packaging
│   │   └── e6_prospect_research.py # Rookie board, models, comps
│   ├── scheduler/
│   │   ├── jobs.py                 # APScheduler job definitions
│   │   └── triggers.py             # Cron/interval configs
│   ├── db/
│   │   ├── session.py              # SQLAlchemy engine and session factory
│   │   ├── models.py               # ORM table definitions (distinct from domain/)
│   │   ├── migrations/             # Alembic migration scripts
│   │   └── repositories/
│   │       ├── leagues.py          # DB read/write for league data
│   │       ├── players.py
│   │       ├── trades.py
│   │       ├── snapshots.py
│   │       └── prospects.py
│   └── config.py                   # Settings (league IDs, sync intervals, etc.)
│
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── api/
│   │   │   └── client.ts           # Axios/fetch wrappers, typed API calls
│   │   ├── components/
│   │   │   ├── dashboard/
│   │   │   ├── league-card/
│   │   │   ├── team-scorecard/
│   │   │   ├── trade-workbench/
│   │   │   ├── manager-dossier/
│   │   │   ├── rookie-board/
│   │   │   └── pick-engine/
│   │   ├── hooks/
│   │   │   └── useLeague.ts        # TanStack Query hooks per domain
│   │   ├── store/
│   │   │   └── ui.ts               # Zustand for pure UI state (active league, panels)
│   │   └── types/
│   │       └── api.ts              # TypeScript types mirroring backend domain models
│   ├── vite.config.ts
│   └── package.json
│
├── data/
│   └── fantasy.db                  # SQLite database (gitignored)
│
└── pyproject.toml / requirements.txt
```

### Structure Rationale

- **adapters/**: All platform-specific code lives here exclusively. Engines never import from adapters. This is the only place Sleeper's JSON shape is known.
- **domain/**: Pydantic models are the contract between the adapter layer and every engine. Changing Sleeper's response format requires only updating mapper.py and nothing else.
- **engines/**: Each engine is an isolated module with a single public function signature: `run(context: EngineContext) -> EngineOutput`. Engines may call each other via the orchestrator, never directly.
- **db/models.py vs domain/models.py**: ORM models (SQLAlchemy) and domain models (Pydantic) are kept separate to avoid coupling persistence concerns to analysis concerns.
- **repositories/**: Thin data access objects so engines do not write SQL directly — they call repositories.

## Architectural Patterns

### Pattern 1: Platform Adapter with Domain Model Contract

**What:** A dedicated adapter layer translates raw external API responses (Sleeper JSON) into internal domain models (Pydantic). All downstream code — engines, routes, repositories — only ever sees domain models.

**When to use:** Whenever a system depends on an external API that may change, or when multiple future platforms must produce the same internal data shape.

**Trade-offs:** Adds a mapping step but eliminates platform coupling from all analysis code. Adding ESPN or Sleeper v2 requires only a new adapter, zero engine changes.

**Example:**
```python
# adapters/sleeper/mapper.py
class SleeperMapper:
    def to_league(self, raw: dict) -> League:
        return League(
            platform_id=raw["league_id"],
            platform="sleeper",
            name=raw["name"],
            season=raw["season"],
            scoring_format=self._map_scoring(raw["scoring_settings"]),
            superflex=self._has_superflex(raw["roster_positions"]),
            tep=self._has_tep(raw["scoring_settings"]),
            roster_size=raw["settings"]["roster_slots"],
        )

# engines/e2_league_context.py — never imports from adapters
def run(league: League, ...) -> LeagueContext:
    return LeagueContext(
        is_superflex=league.superflex,
        scoring_format=league.scoring_format,
        ...
    )
```

### Pattern 2: Engine Orchestrator with Explicit Execution Order

**What:** A central orchestrator function accepts a request context and runs engines in dependency order, threading outputs from earlier engines into later ones.

**When to use:** When multiple engines have inter-dependencies and callers should not need to know the resolution order.

**Trade-offs:** Adds indirection but makes dependencies explicit and testable. Individual engines remain pure functions.

**Example:**
```python
# engines/orchestrator.py
def generate_team_recommendation(league_id: str, roster_id: str, db) -> TeamRecommendation:
    league = league_repo.get(league_id, db)
    roster = roster_repo.get(roster_id, db)
    players = player_repo.get_all(db)

    # Execution order is explicit and documented here
    global_baseline = e1_global_baseline.run(players)
    league_context = e2_league_context.run(league)
    team_direction = e3_team_direction.run(
        roster=roster,
        baseline=global_baseline,
        context=league_context,
    )
    return TeamRecommendation(
        scorecard=team_direction.scorecard,
        direction=team_direction.primary_direction,
        confidence=team_direction.confidence,
        alternates=team_direction.alternate_directions,
    )
```

### Pattern 3: Snapshot-as-Record (Event Sourcing Lite)

**What:** Rather than overwriting analysis results in place, write a new snapshot record with a timestamp each time analysis runs. Keep history immutable. Read latest via `ORDER BY created_at DESC LIMIT 1`.

**When to use:** When recommendation retrospectives, trend tracking, and season-over-season comparison are required features.

**Trade-offs:** Storage grows over time but remains trivial at single-user scale. Enables "were my direction calls right?" retrospectives without separate audit infrastructure.

**Example (schema pattern):**
```sql
CREATE TABLE team_snapshots (
    id            INTEGER PRIMARY KEY,
    league_id     TEXT NOT NULL,
    roster_id     TEXT NOT NULL,
    snapshot_week INTEGER,
    snapshot_date TEXT NOT NULL,  -- ISO date
    direction     TEXT NOT NULL,  -- TeamDirection enum
    confidence    REAL NOT NULL,  -- 0.0–1.0
    scorecard     TEXT NOT NULL,  -- JSON blob of sub-scores
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
-- Always append. Read latest: WHERE roster_id = ? ORDER BY created_at DESC LIMIT 1
```

## Data Flow

### Engine Execution Flow (team recommendation request)

```
Frontend: GET /teams/{roster_id}/recommendation
    |
FastAPI Router (thin validation, route dispatch)
    |
Engine Orchestrator
    |
    +-- E2: League Context Engine
    |       reads: leagues table
    |       writes: LeagueContext (in-memory, passed forward)
    |
    +-- E1: Global Asset Baseline
    |       reads: players table, global_values table
    |       writes: BaselineContext (in-memory)
    |
    +-- E3: Team Direction Engine
    |       reads: rosters table, picks table
    |       inputs: LeagueContext, BaselineContext
    |       writes: DirectionResult (in-memory) + team_snapshots (DB)
    |
    returns: TeamRecommendation (Pydantic → JSON)
    |
Frontend: TanStack Query caches result, renders scorecard
```

### Data Sync Flow (Sleeper ingest)

```
APScheduler trigger (startup / interval / manual /sync endpoint)
    |
SleeperAdapter.sync_league(league_id)
    |
    +-- SleeperClient: GET /league/{id}
    +-- SleeperClient: GET /league/{id}/rosters
    +-- SleeperClient: GET /league/{id}/users
    +-- SleeperClient: GET /league/{id}/transactions/{week}
    +-- SleeperClient: GET /league/{id}/traded_picks
    |
SleeperMapper: raw JSON → domain models (League, Roster, Pick, Trade, Manager)
    |
Repository layer: upsert to SQLite (leagues, rosters, picks, transactions, managers)
    |
    writes: raw_cache table (Sleeper JSON keyed by endpoint+params, TTL)
    writes: normalized domain tables
    sets:   sync_log entry (timestamp, league_id, status)
    |
Analysis engines do NOT run on sync — analysis is on-demand per request
```

### Key Data Flows

1. **Sync-then-analyze separation:** Data ingest (Sleeper → DB) is completely separate from analysis (DB → engine → recommendation). Ingest writes raw data; analysis reads it on demand. No sync triggers automatic engine runs.
2. **League context as a prerequisite:** E2 (League Context) runs before E1 in practice because E1 needs format context to compute format-adjusted values. The orchestrator enforces this order.
3. **Cross-league portfolio flow:** Portfolio queries aggregate across league-specific snapshots by joining on `user_id`. Portfolio engine is a read-only aggregation layer over existing team snapshots, not a new analysis engine.
4. **Manual override flow:** UI posts overrides (e.g., corrected roster position, direction label correction) to `/corrections` endpoint. Corrections are stored in a corrections table. Engines check for overrides before computing and apply them. Overrides never mutate source data.

## Database Schema Patterns

### Core Tables

```sql
-- Platform-agnostic league record
CREATE TABLE leagues (
    id              TEXT PRIMARY KEY,   -- internal UUID
    platform_id     TEXT NOT NULL,      -- Sleeper's league_id
    platform        TEXT NOT NULL,      -- 'sleeper'
    name            TEXT NOT NULL,
    season          INTEGER NOT NULL,
    scoring_format  TEXT NOT NULL,      -- 'ppr' | 'half_ppr' | 'std'
    superflex       INTEGER NOT NULL DEFAULT 0,
    tep             INTEGER NOT NULL DEFAULT 0,
    settings_json   TEXT NOT NULL,      -- full normalized settings as JSON
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- One roster per team per league
CREATE TABLE rosters (
    id              TEXT PRIMARY KEY,
    league_id       TEXT NOT NULL REFERENCES leagues(id),
    platform_roster_id TEXT NOT NULL,
    owner_id        TEXT,               -- references managers.id
    name            TEXT,
    players_json    TEXT NOT NULL,      -- JSON array of player IDs on roster
    taxi_json       TEXT,               -- JSON array of taxi squad player IDs
    ir_json         TEXT,               -- JSON array of IR player IDs
    wins            INTEGER DEFAULT 0,
    losses          INTEGER DEFAULT 0,
    points_for      REAL DEFAULT 0,
    points_against  REAL DEFAULT 0,
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Global player registry (refreshed periodically from Sleeper /players)
CREATE TABLE players (
    id              TEXT PRIMARY KEY,   -- Sleeper player_id
    name            TEXT NOT NULL,
    position        TEXT NOT NULL,      -- QB, RB, WR, TE, K, DEF
    nfl_team        TEXT,
    age             INTEGER,
    years_exp       INTEGER,
    college         TEXT,
    draft_year      INTEGER,
    draft_round     INTEGER,
    draft_pick      INTEGER,
    status          TEXT,               -- 'Active', 'Injured Reserve', 'PUP', etc.
    injury_status   TEXT,
    metadata_json   TEXT,               -- full player object cached as JSON
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Draft picks associated with leagues
CREATE TABLE draft_picks (
    id              TEXT PRIMARY KEY,
    league_id       TEXT NOT NULL REFERENCES leagues(id),
    season          INTEGER NOT NULL,
    round           INTEGER NOT NULL,
    original_owner_id TEXT,            -- roster who the pick originated from
    current_owner_id  TEXT,            -- roster who currently holds it
    previous_owner_id TEXT,
    pick_type       TEXT NOT NULL DEFAULT 'future', -- 'future' | 'current'
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Managers (one per user per league — behavior is league-scoped)
CREATE TABLE managers (
    id              TEXT PRIMARY KEY,
    league_id       TEXT NOT NULL REFERENCES leagues(id),
    platform_user_id TEXT NOT NULL,
    display_name    TEXT,
    team_name       TEXT,
    roster_id       TEXT REFERENCES rosters(id),
    dossier_json    TEXT,               -- current dossier state as JSON
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Transactions (trades + FA/waiver activity)
CREATE TABLE transactions (
    id              TEXT PRIMARY KEY,
    league_id       TEXT NOT NULL REFERENCES leagues(id),
    type            TEXT NOT NULL,      -- 'trade' | 'free_agent' | 'waiver'
    week            INTEGER,
    season          INTEGER,
    status          TEXT NOT NULL,      -- 'complete' | 'failed' | 'vetoed'
    roster_ids_json TEXT NOT NULL,      -- JSON array of involved roster IDs
    adds_json       TEXT,               -- JSON: {player_id: roster_id}
    drops_json      TEXT,               -- JSON: {player_id: roster_id}
    draft_picks_json TEXT,              -- JSON: traded pick objects
    created_at      TEXT NOT NULL,      -- Sleeper transaction timestamp
    ingested_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Immutable analysis snapshots (append-only)
CREATE TABLE team_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    league_id       TEXT NOT NULL REFERENCES leagues(id),
    roster_id       TEXT NOT NULL REFERENCES rosters(id),
    snapshot_week   INTEGER,
    direction       TEXT NOT NULL,
    confidence      REAL NOT NULL,
    scorecard_json  TEXT NOT NULL,      -- full sub-score breakdown
    action_items_json TEXT,             -- top 3 recommendations at snapshot time
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Prospect / historical data (Phase 4)
CREATE TABLE prospects (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    position        TEXT NOT NULL,
    draft_year      INTEGER NOT NULL,
    draft_round     INTEGER,
    draft_pick      INTEGER,
    college         TEXT,
    age_at_draft    REAL,
    combine_json    TEXT,               -- testing metrics as JSON
    college_stats_json TEXT,
    archetype       TEXT,
    tier            TEXT,
    comps_json      TEXT,               -- historical comp player IDs
    outcome_json    TEXT,               -- actual career outcome (for backtesting)
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Raw API cache (avoid repeated calls within TTL)
CREATE TABLE api_cache (
    cache_key       TEXT PRIMARY KEY,   -- hash of endpoint + params
    platform        TEXT NOT NULL,
    response_json   TEXT NOT NULL,
    fetched_at      TEXT NOT NULL DEFAULT (datetime('now')),
    ttl_seconds     INTEGER NOT NULL DEFAULT 3600
);

-- Manual corrections and overrides
CREATE TABLE corrections (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type     TEXT NOT NULL,      -- 'player' | 'team' | 'league' | 'pick'
    entity_id       TEXT NOT NULL,
    field           TEXT NOT NULL,
    original_value  TEXT,
    corrected_value TEXT NOT NULL,
    note            TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Sync audit log
CREATE TABLE sync_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    league_id       TEXT,
    platform        TEXT NOT NULL,
    sync_type       TEXT NOT NULL,      -- 'full' | 'transactions' | 'rosters'
    status          TEXT NOT NULL,      -- 'success' | 'partial' | 'failed'
    records_fetched INTEGER,
    error_message   TEXT,
    started_at      TEXT NOT NULL,
    completed_at    TEXT
);
```

### Schema Indexing Strategy

```sql
-- Frequent query patterns that need indexes
CREATE INDEX idx_rosters_league ON rosters(league_id);
CREATE INDEX idx_picks_league_season ON draft_picks(league_id, season);
CREATE INDEX idx_transactions_league_type ON transactions(league_id, type);
CREATE INDEX idx_snapshots_roster_date ON team_snapshots(roster_id, created_at DESC);
CREATE INDEX idx_managers_league ON managers(league_id);
CREATE INDEX idx_prospects_position_year ON prospects(position, draft_year);
```

## API Layer Design

### REST Endpoint Map

| Endpoint | Method | Purpose | Engine(s) |
|----------|--------|---------|-----------|
| `/leagues` | GET | List all tracked leagues | — |
| `/leagues/{id}/sync` | POST | Trigger manual sync for one league | Adapter |
| `/leagues/{id}/context` | GET | Normalized league settings | E2 |
| `/leagues/{id}/teams` | GET | All roster summaries for league | E3 |
| `/leagues/{id}/teams/{roster_id}` | GET | Full team scorecard + direction | E1, E2, E3 |
| `/leagues/{id}/managers` | GET | All manager dossiers | E4 |
| `/leagues/{id}/managers/{id}/dossier` | GET | Full manager dossier | E4 |
| `/leagues/{id}/trade/evaluate` | POST | Score a proposed trade | E1, E2, E3, E4, E5 |
| `/leagues/{id}/trade/path` | POST | Find better trade paths | E5 |
| `/leagues/{id}/picks` | GET | All picks with valuation | E1, E2, E6 |
| `/rookies` | GET | Rookie board (global + league-adjusted) | E6 |
| `/rookies/{player_id}` | GET | Full prospect profile + comps | E6 |
| `/players/{id}/value` | GET | Player value in context of league | E1, E2 |
| `/portfolio` | GET | Cross-league exposure summary | Read-only aggregation |
| `/sync` | POST | Trigger sync for all leagues | Adapter |
| `/corrections` | POST | Submit manual override | — |

### Response Shape Convention

Every engine output wraps in a consistent envelope:

```json
{
  "data": { ... },
  "confidence": 0.82,
  "reasoning": ["String explaining why this recommendation was made"],
  "caveats": ["What could break this thesis"],
  "generated_at": "2026-03-11T14:30:00Z"
}
```

This gives the frontend everything needed to render opinionated recommendations with visible uncertainty — a first-class requirement from PROJECT.md.

### Frontend State Management

- **TanStack Query** manages all server state (league data, scorecards, dossiers). Handles caching, background refresh, and stale-while-revalidate.
- **Zustand** handles pure UI state: active league, open panels, sidebar state, selected trade proposal in progress.
- No Redux. The domain is read-heavy with infrequent mutations (sync + corrections). TanStack Query is the right tool.

## Build Order (What Must Exist Before What)

```
Phase 1 Prerequisites → Phase 2 Prerequisites → Phase 3+ Prerequisites

[1] SQLite schema + migrations (Alembic)
      ↓
[2] SleeperAdapter (client + mapper) — produces domain models
      ↓
[3] Repository layer (leagues, rosters, picks, players, managers, transactions)
      ↓
[4] Sync Scheduler — populates DB from Sleeper
      ↓
[5] E2: League Context Engine — needed by all other engines
[5] E1: Global Asset Baseline — needed by E3, E5, E6
      ↓
[6] E3: Team Direction Engine — primary value delivery (scorecard, direction)
      ↓
[7] FastAPI routes: /leagues, /teams (first usable frontend)
      ↓
[8] React frontend: league cards, team scorecard
      ↓ (Phase 2)
[9] E4: Manager Behavior Engine (requires transaction history from sync)
[9] E5: Trade Pathing Engine (requires E1, E2, E3, E4)
      ↓
[10] FastAPI routes: /managers, /trade/evaluate, /trade/path
      ↓ (Phase 3)
[11] E6: Prospect Research Engine — pick valuation, rookie board
      ↓ (Phase 4)
[12] Historical prospect database (separate ETL from NFL draft history sources)
[12] Feature models (scikit-learn), backtesting, archetype clustering
```

### Dependency Constraints

- E4 (Manager Behavior) degrades gracefully if transaction history is sparse — outputs low-confidence dossier rather than failing. Build it in Phase 2 but design for partial data from day one.
- E6 (Prospect Research) has two distinct modes: live season mode (rookie board from current class) and historical mode (Phase 4 feature models). Phase 3 builds live mode only; Phase 4 adds the historical lab.
- The snapshot system (team_snapshots table) should be wired in Phase 1 even though retrospective UI comes in Phase 5 — appending snapshots costs nothing and losing early history cannot be recovered.

## Patterns to Follow

### Platform Decoupling via Adapter Protocol

Define an abstract base for platform adapters so the sync scheduler and orchestrator code never references Sleeper directly:

```python
# adapters/base.py
from abc import ABC, abstractmethod
from backend.domain.models import League, Roster, Player, Transaction

class AbstractPlatformAdapter(ABC):
    @abstractmethod
    def get_league(self, platform_id: str) -> League: ...
    @abstractmethod
    def get_rosters(self, league: League) -> list[Roster]: ...
    @abstractmethod
    def get_transactions(self, league: League, week: int) -> list[Transaction]: ...
    @abstractmethod
    def get_players(self) -> list[Player]: ...
```

The sync scheduler accepts any `AbstractPlatformAdapter`. Adding ESPN means implementing this protocol — zero changes to the scheduler, engines, or routes.

### Confidence Score Composition

Each engine returns a confidence level (0.0–1.0) with its output. The orchestrator does not average these — it threads them into the recommendation with explicit reasoning. Low-confidence sub-scores surface as caveats, not hidden averages.

### Format-Aware Value Adjustment

E1 (Global Asset Baseline) computes raw values. E2 produces a `LeagueContext` with format multipliers. E3 applies multipliers when computing scores. This means the same player has a correctly different value in a superflex league versus a single-QB league without any special-casing in E3.

## Anti-Patterns

### Anti-Pattern 1: Engines Calling Sleeper Directly

**What people do:** Call `requests.get("https://api.sleeper.app/...")` from inside an analysis engine when they need fresh data.

**Why it's wrong:** Couples every engine to Sleeper's API shape. A Sleeper endpoint change breaks analysis logic. Makes engines untestable without network access. Prevents adding future platforms.

**Do this instead:** Engines only read from the DB (via repositories). Data is already synced by the adapter layer. If freshness is needed, trigger a sync first, then run the engine.

### Anti-Pattern 2: Single Opaque Score

**What people do:** Compute one "overall team value" number and present it as the recommendation.

**Why it's wrong:** Hides what drives the number. A rebuilding team with great pick capital and a win-now team with aging stars can have the same opaque score. Makes the system untrustworthy because users can't validate the reasoning.

**Do this instead:** Maintain all sub-scores (win-now, future value, depth, pick capital, etc.) separately throughout the pipeline. Compose into direction only at the end. Always expose sub-scores alongside any summary recommendation.

### Anti-Pattern 3: Analysis Logic in Routes

**What people do:** Put trade evaluation math, player value logic, or direction detection in FastAPI route handlers for expediency.

**Why it's wrong:** Route handlers are untestable without HTTP context. Logic becomes duplicated as more routes need the same computation. Impossible to run analysis outside the HTTP request cycle (e.g., background jobs, CLI testing).

**Do this instead:** Routes only validate input, call the orchestrator, and serialize the response. All logic lives in engines. Engines are plain Python functions testable with `pytest` without starting a server.

### Anti-Pattern 4: Mutable Snapshots

**What people do:** Update analysis results in-place — overwriting the previous recommendation with the new one.

**Why it's wrong:** Destroys the ability to answer "was this recommendation calibrated?" or "how did this team's direction change over the season?" Retrospective features (Phase 5) become impossible to build.

**Do this instead:** Always append new snapshot rows. Never UPDATE team_snapshots. Read the latest via created_at DESC LIMIT 1.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Sleeper API | Polling via APScheduler background job, HTTP GET, read-only | Stay under 1,000 calls/minute. Cache responses in api_cache table. No auth required. Player database endpoint returns all ~10k players; call infrequently (daily or weekly). |
| NFLverse / nfl-data-py | Optional batch import for historical prospect data (Phase 4) | One-time ETL for historical prospect outcomes, not ongoing sync. |

### Internal Boundaries

| Boundary | Communication | Constraint |
|----------|---------------|------------|
| Adapter → Domain | SleeperMapper returns Pydantic models | Mapper is the only code that knows Sleeper's JSON shape |
| Domain → Engines | Orchestrator passes Pydantic models as function arguments | Engines never import from adapters/ |
| Engines → DB | Engines call repositories; never execute SQL directly | Repository is the only code that writes ORM queries |
| Orchestrator → Routes | Routes call orchestrator functions; receive Pydantic response models | Routes never instantiate engines directly |
| Frontend → Backend | HTTP REST, JSON, TanStack Query caches responses | Frontend has no direct DB access; all data through API |
| Engines → Engines | E3 receives output of E1 and E2 as arguments passed by orchestrator | Engines never import each other — orchestrator owns dependency threading |

## Scaling Considerations

This is a single-user local app. Scale concerns are limited to data volume and cold start time, not concurrency.

| Concern | At 1–3 leagues | At 10+ leagues |
|---------|---------------|----------------|
| Sync time | < 5 seconds per league | Add async sync with asyncio.gather; still within APScheduler |
| Engine computation | Sub-second for all engines | No change; still in-process Python |
| DB size | < 50MB after years of operation | SQLite handles this trivially |
| Cold start | Full sync on startup optional; load from DB immediately, sync in background | Background sync on startup rather than blocking start |
| Prospect historical DB (Phase 4) | Larger dataset but read-only at runtime | Pre-computed feature matrices; no real-time model training |

The architecture intentionally avoids Celery, Redis, Kafka, or any external infrastructure. For a local single-user tool, these add operational overhead with no benefit. APScheduler embedded in the FastAPI process is the right level of complexity.

## Sources

- [Sleeper API Documentation](https://docs.sleeper.com/) — HIGH confidence, authoritative source for all endpoint capabilities and data shapes
- [Architecting a Fantasy Football Trade Analyzer](https://dev.to/ffteamnames/architecting-a-fantasy-football-trade-analyzer-apis-algorithms-and-avoiding-bias-1a76) — MEDIUM confidence, community source documenting FastAPI + React + pandas trade analysis pattern
- [TanStack Query](https://tanstack.com/query/latest) — HIGH confidence, official docs for server-state management
- [Implementing Background Job Scheduling in FastAPI with APScheduler](https://bytegoblin.io/blog/implementing-background-job-scheduling-in-fastapi-with-apscheduler.mdx) — MEDIUM confidence, confirms APScheduler + SQLAlchemyJobStore pattern
- [Fantasy Sports Engine Architecture Core Modules](https://www.arkasoftwares.com/blog/fantasy-sports-engine-architecture-core-modules/) — MEDIUM confidence, describes event-driven engine separation patterns
- [Data Pipeline Architecture Patterns](https://dagster.io/guides/data-pipeline-architecture-5-design-patterns-with-examples) — MEDIUM confidence, adapter and decoupling pattern validation
- [GitHub: fantasy-football-ai (cbratkovics)](https://github.com/cbratkovics/fantasy-football-ai) — MEDIUM confidence, production ML system for fantasy forecasting with FastAPI inference pattern

---
*Architecture research for: Dynasty Fantasy Football Front Office OS*
*Researched: 2026-03-11*
