---
phase: 11-roster-lineup-intelligence
plan: 02
subsystem: api
tags: [lineup, hygiene, fastapi, intelligence, duckdb]
requires:
  - phase: 11-01
    provides: lineup schema, models, constants, and repo persistence
provides:
  - LineupEngine replacement-level computation and title-window classification
  - HygieneEngine suggestion generation for consolidate/cut/stash/taxi
  - IntelligenceService wiring for lineup+hygiene with contender fragility post-adjustment
  - Intelligence and leagues API routes for lineup, hygiene, taxi config, and slot occupancy
affects: [intelligence, lineup, hygiene, routers, frontend-api-consumers]
tech-stack:
  added: []
  patterns: [league-normalized scoring, lazy cache-on-read intelligence fetches, roster hygiene ordering]
key-files:
  created:
    - backend/src/fantasy/lineup/lineup_engine.py
    - backend/src/fantasy/lineup/hygiene_engine.py
    - backend/src/fantasy/routers/leagues.py
    - backend/tests/lineup/test_lineup_engine.py
    - backend/tests/lineup/test_hygiene_engine.py
    - backend/tests/integration/test_intelligence_router.py
  modified:
    - backend/src/fantasy/intelligence/intelligence_service.py
    - backend/src/fantasy/routers/intelligence.py
    - backend/src/fantasy/main.py
    - backend/tests/lineup/__init__.py
key-decisions:
  - "Lineup scoring normalizes each starter slot across league to avoid lineup-length skew."
  - "Direction post-adjustment applies only when contender labels collide with Outside Window."
  - "Hygiene output ordering is deterministic: consolidate, cut, stash, taxi."
patterns-established:
  - "Use LineupRepo as the single persistence facade for lineup/hygiene caches."
  - "Expose per-roster intelligence slices through lazy compute-on-miss service methods."
requirements-completed: [FS-02, FS-04]
duration: 1 min
completed: 2026-03-25
---

# Phase 11 Plan 02: Lineup and Hygiene Intelligence Summary

**Shipped lineup viability scoring and roster hygiene recommendation engines, then wired them end-to-end through intelligence service and league/intelligence API routes.**

## Performance

- **Duration:** 1 min
- **Started:** 2026-03-24T22:42:14-04:00
- **Completed:** 2026-03-25T02:43:47Z
- **Tasks:** 3
- **Files modified:** 10

## Accomplishments
- Implemented `LineupEngine` with replacement-level baselines, league normalization, and title-window labels.
- Implemented `HygieneEngine` covering consolidation, cut, stash, and taxi suggestions with ordering and caps.
- Wired lineup/hygiene computation and persistence into `IntelligenceService` and exposed `/intelligence/*` plus `/leagues/*` endpoints.
- Added unit and integration coverage for engine behavior and API contract responses.

## Task Commits

Each task was committed atomically:

1. **Task 1: Build LineupEngine with replacement-level computation and title-window classifier** - `c9249ea` (feat)
2. **Task 2: Build HygieneEngine with consolidation, cut, stash, and taxi suggestions** - `2d7dd08` (feat)
3. **Task 3: Wire engines into IntelligenceService, add direction post-adjustment, extend routers** - `a6e2e28` (feat)

## Files Created/Modified
- `backend/src/fantasy/lineup/lineup_engine.py` - lineup slot scoring and title-window classifier.
- `backend/src/fantasy/lineup/hygiene_engine.py` - hygiene suggestion engine.
- `backend/src/fantasy/intelligence/intelligence_service.py` - lineup/hygiene integration and lazy getters.
- `backend/src/fantasy/routers/intelligence.py` - lineup/hygiene endpoints.
- `backend/src/fantasy/routers/leagues.py` - taxi config and slot occupancy endpoints.
- `backend/src/fantasy/main.py` - leagues router registration.
- `backend/tests/lineup/test_lineup_engine.py` - lineup engine unit tests.
- `backend/tests/lineup/test_hygiene_engine.py` - hygiene engine unit tests.
- `backend/tests/integration/test_intelligence_router.py` - integration tests for new intelligence/leagues endpoints.

## Decisions Made
- Persisted lineup/hygiene via `LineupRepo` and exposed read-through service getters for cache misses.
- Kept title-window label thresholds strictly tied to constants for API consistency.
- Kept hygiene recommendation ordering stable to support deterministic client rendering.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Python executable mismatch in verification commands**
- **Found during:** Task 1 verification
- **Issue:** `python` executable was unavailable in runtime shell.
- **Fix:** Switched execution to `uv run ...` for pytest/python checks.
- **Files modified:** None
- **Verification:** All unit/integration commands passed via `uv run`.
- **Committed in:** N/A (execution environment adjustment)

**2. [Rule 3 - Blocking] Integration test path mismatch**
- **Found during:** Task 3 verification
- **Issue:** Required test path `backend/tests/integration/test_intelligence_router.py` did not exist.
- **Fix:** Added integration-path test module to satisfy planned verification and acceptance criteria.
- **Files modified:** `backend/tests/integration/test_intelligence_router.py`
- **Verification:** `uv run pytest tests/integration/test_intelligence_router.py -x -v` passed.
- **Committed in:** `a6e2e28`

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** No scope creep; both fixes were necessary to execute planned verification successfully.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Core lineup and hygiene intelligence logic is complete and API-accessible.
- Ready for `11-03` UI integration and downstream consumer wiring.

## Self-Check: PASSED

- All 3 tasks executed and committed atomically
- Required SUMMARY created
- Verification commands passed
- No unresolved blockers

---
*Phase: 11-roster-lineup-intelligence*
*Completed: 2026-03-25*
