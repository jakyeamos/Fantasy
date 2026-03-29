---
phase: 13-context-awareness
plan: "02"
subsystem: api
tags: [calendar-service, freshness-service, fastapi, ingest]
requires:
  - phase: 13-01
    provides: context models, constants, repo, and persistence tables
provides:
  - Calendar/freshness services, context API routes, and ingest freshness updates
affects: [13-03, 13-04]
tech-stack:
  added: []
  patterns:
    - date-sensitive logic is isolated in services with injected time sources
    - ingest marks freshness domains at the point data is refreshed
key-files:
  created:
    - backend/src/fantasy/context/calendar_service.py
    - backend/src/fantasy/context/freshness_service.py
    - backend/src/fantasy/routers/context.py
  modified:
    - backend/src/fantasy/main.py
    - backend/src/fantasy/ingestion/ingest_service.py
    - backend/tests/test_calendar_state.py
    - backend/tests/test_freshness.py
requirements-completed: [FS-03, FS-08]
duration: retroactive
completed: 2026-03-27
---

# 13-02 Summary

Completed the service layer and API surface for context awareness.

- Added `CalendarService` with automatic window detection plus manual override support.
- Added `FreshnessService` with stale/fresh/never-updated tagging and warning generation per domain.
- Exposed calendar and freshness endpoints through `/context`.
- Marked `injuries`, `depth_chart`, `draft_capital`, and `landing_spots` freshness domains during ingest flows where those datasets are refreshed.

Verification:

- `backend/.venv/bin/python -m pytest backend/tests/test_calendar_state.py backend/tests/test_freshness.py -q`
- `backend/.venv/bin/python -m pytest backend/tests -q` (only unrelated lineup replacement-level failures remained)

