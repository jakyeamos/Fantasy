---
phase: 06-dynamic-pick-valuation
plan: "01"
subsystem: database
tags: [duckdb, pydantic, alembic, picks, dynasty, pick-valuation]

requires:
  - phase: 05-trade-intelligence
    provides: TradedPick/TradeAsset model from trade/models.py — used as pick identity in PickValuationContext
  - phase: 04-manager-profiling
    provides: team_directions table with primary_label — used for rebuilder count and manager demand signals
  - phase: 01-sleeper-ingestion
    provides: standings and picks tables — primary raw inputs for pick valuation

provides:
  - "backend/src/fantasy/picks/ package: constants.py, models.py, pick_repo.py"
  - "All Phase 6 named constants (CALENDAR_TIMING_MULTIPLIERS, DIRECTION_DEMAND_MAP, timing thresholds)"
  - "Pydantic models: PickValue, PickValuationContext, LeaguePickContext, TimingLabel, TeamStandingsRow"
  - "PickRepo: get_standings, get_league_pick_context, get_manager_demand_factor, get_all_picks, save_pick_values"
  - "Alembic migration 009_pick_values.py: pick_values table DDL with UNIQUE constraint"
  - "Test stubs for Plans 02 and 03"

affects:
  - 06-02 (PickEngine implementation builds against these contracts)
  - 06-03 (picks router depends on PickRepo and models)
  - 07-rookie-board (Phase 7 injects class_strength_signal into PickValuationContext)

tech-stack:
  added: []
  patterns:
    - "picks/ package follows same layout as trade/: __init__.py, constants.py, models.py, {name}_repo.py"
    - "Phase 7 injection hook: named typed Pydantic field (class_strength_signal) defaults to 0.0; Phase 7 can inject non-zero without engine changes"
    - "PickRepo follows same DuckDB connection injection pattern as TradeRepo"

key-files:
  created:
    - backend/src/fantasy/picks/__init__.py
    - backend/src/fantasy/picks/constants.py
    - backend/src/fantasy/picks/models.py
    - backend/src/fantasy/picks/pick_repo.py
    - backend/alembic/versions/009_pick_values.py
    - backend/tests/picks/__init__.py
    - backend/tests/picks/test_pick_engine.py
    - backend/tests/picks/test_pick_repo.py
    - backend/tests/integration/test_pick_router.py
  modified: []

key-decisions:
  - "Migration numbered 009 (not 007 as planned) because 007_roster_owner_display_name and 008_manager_profile_trade_history already exist in the codebase"
  - "PickValuationContext uses TradeAsset (not a separate TradedPick model) since that is the pick identity model from Phase 5"
  - "save_pick_values signature takes explicit league_id param to avoid misuse with pick.pick_owner_roster_id"

patterns-established:
  - "Pattern 1: All Phase 6 pick formula constants are in constants.py — engine code reads constants, never embeds numbers"
  - "Pattern 2: Phase 7 hook is class_strength_signal float field on PickValuationContext, default=0.0; formula uses CLASS_STRENGTH_WEIGHT=0.20 so Phase 7 injection is live without code changes"
  - "Pattern 3: PickRepo always falls back to neutral defaults rather than raising on missing data (Pitfall 3)"

requirements-completed: [PICK-01, PICK-02]

duration: 3min
completed: 2026-03-22
---

# Phase 06 Plan 01: Dynamic Pick Valuation Foundation Summary

**picks/ package with CALENDAR_TIMING_MULTIPLIERS, DIRECTION_DEMAND_MAP, PickValue/PickValuationContext/LeaguePickContext Pydantic models, PickRepo DuckDB layer, pick_values Alembic migration (009), and test stubs for Plans 02-03**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-22T18:11:05Z
- **Completed:** 2026-03-22T18:14:00Z
- **Tasks:** 2/2
- **Files modified:** 9 created

## Accomplishments

- Created `backend/src/fantasy/picks/` package with all 58 named constants across slot decay, calendar timing, class strength hook, rebuilder demand, per-manager demand, and timing thresholds
- Created Pydantic domain models including `PickValuationContext.class_strength_signal` Phase 7 injection hook (default=0.0, range [-1, +1])
- Created `PickRepo` with 5 methods: standings with trend window (pitfall 1 guard), league rebuilder count (pitfall 3 fallback), manager demand factor (sigmoid + evidence floor), picks reader, and pick_values upsert
- Created migration `009_pick_values.py` with full pick_values DDL and UNIQUE constraint

## Task Commits

1. **Task 1: Create picks package with constants and models** - `b3a999a` (feat)
2. **Task 2: Create PickRepo, Alembic migration, and test stubs** - `efd2a0f` (feat)

## Files Created/Modified

- `backend/src/fantasy/picks/__init__.py` - Empty package marker
- `backend/src/fantasy/picks/constants.py` - All 58+ named Phase 6 constants including CALENDAR_TIMING_MULTIPLIERS, DIRECTION_DEMAND_MAP, TIMING_REASONING_TEMPLATES
- `backend/src/fantasy/picks/models.py` - PickValue, PickValuationContext (Phase 7 hook), LeaguePickContext, TeamStandingsRow, TimingLabel enum
- `backend/src/fantasy/picks/pick_repo.py` - PickRepo with 5 DuckDB methods; graceful fallbacks throughout
- `backend/alembic/versions/009_pick_values.py` - pick_values DDL with UNIQUE(league_id, pick_owner_roster_id, pick_year, pick_round)
- `backend/tests/picks/__init__.py` - Empty package marker
- `backend/tests/picks/test_pick_engine.py` - Stub for Plan 02
- `backend/tests/picks/test_pick_repo.py` - Stub for Plan 02
- `backend/tests/integration/test_pick_router.py` - Stub for Plan 03

## Decisions Made

- Migration numbered 009 rather than 007 as planned — 007 and 008 already exist in codebase (007_roster_owner_display_name, 008_manager_profile_trade_history); auto-fixed per Rule 1
- `PickValuationContext.pick` uses `TradeAsset` from `fantasy.trade.models` (the existing pick identity type) rather than a new `TradedPick` model that does not exist in the Phase 5 codebase
- `save_pick_values` takes an explicit `league_id: str` parameter rather than deriving it from the pick object to avoid ambiguity

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Migration renumbered from 007 to 009**
- **Found during:** Task 2 (Alembic migration creation)
- **Issue:** Plan specified `007_pick_values.py` but `007_roster_owner_display_name.py` and `008_manager_profile_trade_history.py` already exist; using 007 would create a duplicate revision ID and break the Alembic chain
- **Fix:** Created `009_pick_values.py` with `down_revision = "008_manager_profile_trade_history"` and noted the renaming in the migration docstring
- **Files modified:** `backend/alembic/versions/009_pick_values.py`
- **Verification:** Migration file parses correctly; Alembic chain is valid
- **Committed in:** efd2a0f (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug)
**Impact on plan:** Required correction for Alembic chain integrity. No scope creep.

## Issues Encountered

None beyond the migration numbering auto-fix.

## Known Stubs

- `backend/tests/picks/test_pick_engine.py` — placeholder test; Plan 02 populates with real engine unit tests
- `backend/tests/picks/test_pick_repo.py` — placeholder test; Plan 02 populates with DuckDB integration tests
- `backend/tests/integration/test_pick_router.py` — placeholder test; Plan 03 populates with router integration tests

These stubs are intentional — this plan's goal is to establish contracts for Plans 02 and 03 to build against. They are not blocking the plan's stated objective.

## Self-Check: PASSED

- All constants are named and typed in constants.py: YES
- `PickValuationContext.class_strength_signal` Phase 7 hook present with default=0.0: YES
- PickRepo importable with all 5 methods: YES
- Migration 009_pick_values.py exists with pick_values DDL and UNIQUE constraint: YES
- Test stubs in tests/picks/ pass: YES (2 passed)

## Next Phase Readiness

- Plan 02 (PickEngine) can build against the full contract: PickValue, PickValuationContext, LeaguePickContext, TeamStandingsRow, PickRepo, all constants
- Plan 03 (picks router) can build against PickRepo and models without any further exploration
- Phase 7 (Rookie Board) can inject class strength by passing non-zero `class_strength_signal` to `PickValuationContext` — no engine changes required

---
*Phase: 06-dynamic-pick-valuation*
*Completed: 2026-03-22*
