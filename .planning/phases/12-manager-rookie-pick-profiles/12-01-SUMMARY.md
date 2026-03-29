---
phase: 12-manager-rookie-pick-profiles
plan: "01"
subsystem: database
tags: [duckdb, alembic, rookie-picks, sleeper]
requires: []
provides:
  - Rookie-pick persistence foundation and draft-pick ingest primitives
affects: [12-02, 12-03, 12-04, 12-05, 12-06]
tech-stack:
  added: []
  patterns:
    - triple-write schema updates across migration, startup compat, and test bootstrap
    - typed Sleeper draft-pick mapping before engine logic
key-files:
  created:
    - backend/src/fantasy/rookie_pick/__init__.py
    - backend/src/fantasy/rookie_pick/constants.py
    - backend/src/fantasy/rookie_pick/models.py
    - backend/src/fantasy/rookie_pick/rookie_pick_repo.py
    - backend/alembic/versions/015_rookie_pick_profiles.py
    - backend/tests/picks/test_rookie_pick_repo.py
  modified:
    - backend/src/fantasy/startup_tasks.py
    - backend/tests/conftest.py
    - backend/src/fantasy/ingestion/sleeper_client.py
    - backend/src/fantasy/ingestion/sleeper_mapper.py
requirements-completed: [FS-06]
duration: retroactive
completed: 2026-03-27
---

# 12-01 Summary

Completed the rookie-pick schema and ingest foundation for Phase 12.

- Added migration `015` plus matching schema-compat definitions for `draft_pick_selections` and `manager_rookie_pick_profiles`.
- Created the `fantasy.rookie_pick` package with constants, models, and repo upsert/read paths.
- Added `SleeperClient.fetch_draft_picks()` and `SleeperMapper.map_draft_pick_selections()` so draft selections can be ingested as typed domain data.
- Seeded the initial repo and integration test files needed for the rest of the phase.

Verification:

- `backend/.venv/bin/python -m pytest backend/tests/picks/test_rookie_pick_repo.py backend/tests/picks/test_package_builder_integration.py backend/tests/picks/test_reroute_picks_buyer.py -q`

