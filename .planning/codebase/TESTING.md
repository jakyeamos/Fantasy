# Testing Patterns

**Analysis Date:** 2026-03-22

## Test Framework

**Runner:**
- pytest 8+
- Config: `backend/pyproject.toml` under `[tool.pytest.ini_options]`
- `asyncio_mode = "auto"` — all async tests run without explicit `@pytest.mark.asyncio`
- `testpaths = ["tests"]`, `pythonpath = ["src"]`

**Assertion Library:**
- pytest built-in `assert` statements
- `pytest.approx` used for floating-point comparisons: `assert result == pytest.approx(0.2)`

**Run Commands:**
```bash
cd backend
python -m pytest                          # Run all tests
python -m pytest tests/test_scorecard_engine.py  # Single file
python -m pytest tests/intelligence/     # By subdirectory
python -m pytest -v                      # Verbose output
```

No coverage target is configured. No watch mode dependency.

**Frontend Testing:**
- No test framework detected in `frontend/package.json`; no `*.test.ts` or `*.spec.tsx` files present
- Frontend is not tested at this time

## Test File Organization

**Location:** All backend tests are co-located in `backend/tests/`, separate from `src/`

**Naming:**
- Unit/engine tests: `test_{module_name}.py` — e.g., `test_scorecard_engine.py`, `test_direction_engine.py`
- Router/integration tests: `test_{router_name}_router.py` — e.g., `test_dashboard_router.py`, `test_profiling_router.py`
- Integration tests with full client: `tests/integration/test_{router}_router.py` — e.g., `tests/integration/test_trade_router.py`
- Subdirectory grouping for larger domains: `tests/intelligence/`, `tests/picks/`, `tests/rookie/`

**Structure:**
```
backend/tests/
├── conftest.py                          # All shared fixtures: db, seed data, mock API responses
├── test_scorecard_engine.py
├── test_direction_engine.py
├── test_valuation_engine.py
├── test_profiling_engine.py
├── test_dashboard_router.py
├── test_profiling_router.py
├── test_ingest_service.py
├── test_sleeper_mapper.py
├── test_nfl_data_loader.py
├── test_startup_tasks.py
├── test_intelligence_router.py
├── test_intelligence_service.py
├── intelligence/
│   ├── test_trade_engine.py
│   ├── test_reroute_engine.py
│   └── test_package_builder.py
├── integration/
│   ├── test_trade_router.py
│   └── test_pick_router.py
├── picks/
│   ├── test_pick_engine.py
│   └── test_pick_repo.py
└── rookie/
    ├── test_rookie_engine.py
    ├── test_rookie_repo.py
    └── test_draft_room.py
```

## Test Structure

**Suite Organization:**
```python
# No class grouping — all tests are top-level functions
def test_all_subscores_present(phase2_seed_data):
    scorecards = ScorecardEngine(phase2_seed_data).compute_all("league_x")
    scorecard = scorecards[1]
    for field in ["win_now", "future_value", ...]:
        assert getattr(scorecard, field) is not None


def test_subscores_in_range(phase2_seed_data):
    scorecards = ScorecardEngine(phase2_seed_data).compute_all("league_x")
    for scorecard in scorecards.values():
        for value in scorecard.as_dict().values():
            assert 0.0 <= value <= 1.0
```

**Patterns:**
- No `describe`/class grouping — all tests are module-level functions
- Each test constructs the system under test inline; no shared `setUp`
- Tests mutate seed data directly via `conn.execute(...)` to set up edge cases
- Arrange-Act-Assert with no `# Arrange/Act/Assert` comments
- Test names are full sentences describing the expected behavior: `test_fragility_availability_proxy`, `test_corrections_applied_before_scoring`

## Mocking

**Framework:** pytest `monkeypatch` for environment variables; hand-written fake classes for external dependencies

**HTTP Mocking — `FakeSleeperClient` pattern:**
```python
# backend/tests/test_ingest_service.py
class FakeSleeperClient:
    def __init__(self, league, rosters, traded_picks, weekly_transactions, week, ...):
        self._league = league
        # ...

    async def fetch_league(self, _league_id):
        return self._league

    async def fetch_transactions(self, _league_id, week):
        return self._weekly_transactions.get(week, [])
```
The `FakeSleeperClient` is a hand-written stub that accepts expected response data and returns it on the matching `async def fetch_*` calls.

**Repo Mocking — `_FakeRepo` inner class pattern:**
```python
# backend/tests/picks/test_pick_engine.py
class _FakeRepo:
    def __init__(self, *, season: int = 2026, class_strength: float | None = 0.0):
        self.season = season
        self.standings = TeamStandingsRow(...)
        self.league_context = LeaguePickContext(...)
        self.demand_by_manager = {1: 0.9, 2: 0.3}

    def get_current_season(self, league_id: str) -> int:
        assert league_id == "league_x"
        return self.season
```
Engines that depend on repos have their `_repo` attribute replaced: `engine._repo = repo or _FakeRepo()`

**Dependency Override — FastAPI pattern:**
```python
# backend/tests/integration/test_trade_router.py
def _override_conn(conn):
    def _getter():
        yield conn
    return _getter

app = create_app()
app.dependency_overrides[get_read_db_conn] = _override_conn(trade_seed_data)
app.dependency_overrides[get_write_db_conn] = _override_conn(trade_seed_data)
client = TestClient(app)
```
All router integration tests follow this exact pattern. A new `app = create_app()` + `TestClient` is created per test.

**Environment Variables:**
```python
monkeypatch.setenv("FANTASY_PORTFOLIO_OWNER_DISPLAY_NAME", "jakye")
get_settings.cache_clear()
try:
    # ... test
finally:
    get_settings.cache_clear()
```
Settings are cleared after each monkeypatch test using `try/finally`.

**What to Mock:**
- External HTTP calls (SleeperClient) — always use FakeSleeperClient
- Repository layer when unit-testing engine math in isolation — use _FakeRepo
- FastAPI dependencies (`get_read_db_conn`, `get_write_db_conn`) in all router tests

**What NOT to Mock:**
- DuckDB in-memory database — used directly as the real persistence layer in all tests
- Engine classes — tested against the real implementation; no engine stubs observed

## Fixtures and Factories

**Location:** All fixtures are in `backend/tests/conftest.py`

**Database Fixture:**
```python
@pytest.fixture
def db():
    conn = duckdb.connect(":memory:")
    for statement in SCHEMA_SQL:
        conn.execute(statement)
    yield conn
    conn.close()
```
The `SCHEMA_SQL` list in `conftest.py` is the authoritative test schema — it mirrors the Alembic migrations manually and must be kept in sync when migrations are added.

**Layered Seed Data Fixtures:**
```python
@pytest.fixture
def phase2_seed_data(db):
    # Inserts leagues, rosters, players, stats, ADP, traded_picks
    return db

@pytest.fixture
def phase3_seed_data(phase2_seed_data):
    # Adds transactions (trades) on top of phase2
    return phase2_seed_data

@pytest.fixture
def profiling_seed_data(phase2_seed_data):
    # Adds team_directions and profiling-specific transactions
    return phase2_seed_data

@pytest.fixture
def trade_seed_data(profiling_seed_data):
    # Runs IntelligenceService + ProfilingEngine to produce computed rows
    return conn
```
Fixtures compose via dependency — `trade_seed_data` depends on `profiling_seed_data` which depends on `phase2_seed_data` which depends on `db`. Pick tests define their own `_seed_pick_data(conn)` helper function rather than using conftest fixtures.

**Mock API Response Fixtures:**
```python
@pytest.fixture
def mock_league_response():
    return {"league_id": "test_league_001", "name": "Test Dynasty League", ...}

@pytest.fixture
def mock_roster_response():
    return {"roster_id": 1, "owner_id": "user_abc", ...}
```
These are plain dict fixtures used to feed `FakeSleeperClient` in ingestion tests.

**Inline Seeding:**
When a test needs a specific edge case not covered by conftest fixtures, it seeds data directly:
```python
def test_missing_stats_defaults(phase2_seed_data):
    phase2_seed_data.execute(
        "INSERT INTO rosters (...) VALUES (3, 'league_x', 3, 'user_c', ...)"
    )
    scorecards = ScorecardEngine(phase2_seed_data).compute_all("league_x")
    assert isinstance(scorecards[3].win_now, float)
```

## Coverage

**Requirements:** None enforced. No `--cov` flag in `pyproject.toml`.

**View Coverage:**
```bash
cd backend
python -m pytest --cov=fantasy --cov-report=term-missing
```

## Test Types

**Unit Tests:**
- Engine math: `test_scorecard_engine.py`, `test_direction_engine.py`, `test_valuation_engine.py`, `test_profiling_engine.py`
- Pure function tests: `test_pick_engine.py` tests standalone functions (`expected_draft_slot`, `slot_to_base_value`, etc.) without DB
- Mapper/transform tests: `test_sleeper_mapper.py`

**Integration Tests:**
- Router tests using `TestClient` + in-memory DuckDB: `test_dashboard_router.py`, `tests/integration/test_trade_router.py`, `tests/integration/test_pick_router.py`
- These tests exercise the full stack: router → engine → repo → DuckDB
- Ingest service tests: `test_ingest_service.py` uses `FakeSleeperClient` + real DuckDB

**E2E Tests:**
- Not present; no Playwright, Cypress, or similar tooling detected

## Common Patterns

**Calling Internal Helpers Directly:**
Router-level private helpers are imported and tested directly to avoid full HTTP overhead:
```python
from fantasy.routers.dashboard import (
    _build_exploit_windows,
    _derive_primary_weakness,
    _derive_summary_signal,
)

def test_dashboard_summary_signal_prefers_pick_capital_edge(phase3_seed_data):
    signal = _derive_summary_signal(phase3_seed_data, "league_x", 1, (...))
    assert signal == "Pick capital edge: 1st of 2 in this league."
```

**Temporal Testing:**
Time-sensitive logic is tested by mutating `created_at` directly in the seed DB:
```python
phase3_seed_data.execute(
    "UPDATE transactions SET created_at = ? WHERE league_id = 'league_x'",
    [datetime.now() - timedelta(days=30)],
)
windows = _build_exploit_windows(phase3_seed_data, "league_x", 1)
assert windows == []
```

**Floating-Point Assertions:**
```python
assert score == pytest.approx(0.2)
assert result.timed_value == pytest.approx(result.base_value * 1.18, abs=0.01)
```

**Negative / Edge Case Testing:**
Missing data (empty players table, missing stats) is tested by deleting rows before exercising the engine:
```python
phase2_seed_data.execute(
    "DELETE FROM player_stats_weekly WHERE player_id IN ('qb1', 'rb1', 'wr1', 'te1')"
)
scorecards = ScorecardEngine(phase2_seed_data).compute_all("league_x")
assert scorecards[1].fragility > scorecards[2].fragility
```

**Async Testing:**
`asyncio_mode = "auto"` means async test functions are declared normally with `async def`:
```python
async def test_ingest_run_creates_records(db, mock_league_response, ...):
    async with FakeSleeperClient(...) as client:
        service = IngestService(db, client)
        await service.run("test_league_001")
    assert db.execute("SELECT COUNT(*) FROM leagues").fetchone()[0] == 1
```

---

*Testing analysis: 2026-03-22*
