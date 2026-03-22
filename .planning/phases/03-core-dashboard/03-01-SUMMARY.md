---
phase: 03-core-dashboard
plan: "01"
subsystem: api
tags: [snapshots, dashboard, duckdb, alembic]
requires:
  - phase: 02
    provides: intelligence output tables
provides:
  - SnapshotService capturing full league state as JSON in league_snapshots table
  - Auto-selects full vs delta type (one full per calendar month, deltas thereafter)
  - Delta tracks changed_players and changed_rosters
  - FastAPI /snapshots router (trigger, status)
  - FastAPI /dashboard router (summary, league detail with risers/fallers, exploit windows)
  - Alembic migration 005 (league_snapshots table)
  - Post-ingest snapshot hook in IngestService
affects: [03-02, 03-03, 09]
tech-stack:
  added: []
  patterns: [snapshot JSON blob in DuckDB, delta computed from two most recent snapshots]
key-files:
  created:
    - backend/src/fantasy/snapshots/snapshot_service.py
    - backend/src/fantasy/snapshots/models.py
    - backend/src/fantasy/routers/snapshots.py
    - backend/src/fantasy/routers/dashboard.py
    - backend/alembic/versions/005_league_snapshots.py
  modified:
    - backend/src/fantasy/ingestion/ingest_service.py
    - backend/src/fantasy/main.py
key-decisions:
  - "One full snapshot per calendar month, deltas thereafter to keep storage manageable"
requirements-completed: [DASH-01, DASH-02, DASH-03, DASH-04, PORT-01]
duration: retroactive
completed: 2026-03-22
---

# Phase 03-01: SnapshotService + Dashboard Router Summary

**Full-state snapshots and dashboard API with risers/fallers and exploit windows.**

## Known Quality Gap

- Dashboard exploit windows (`_build_exploit_windows()`) derived entirely from raw transaction patterns — does not use pre-computed `manager_profiles` / `manager_pitch_angles` from Phase 4
- PORT-01 (cross-league concentration risk alerts) not implemented; behavioral triggers present but player ownership concentration surface deferred to Phase 9
