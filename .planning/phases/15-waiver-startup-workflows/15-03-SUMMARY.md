---
phase: 15-waiver-startup-workflows
plan: "03"
subsystem: backend
tags: [startup, picks, engine, tdd]
requires:
  - phase: 15-01
    provides: startup models, constants, and schema support
provides:
  - Startup draft context engine with mode detection, build templates, and pick trade heuristics
affects: [15-05, 15-06]
tech-stack:
  added: []
  patterns:
    - standalone helpers for startup detection and build-template mapping
    - pick recommendations derived from current pick-values instead of draft-specific duplicates
key-files:
  created: []
  modified:
    - backend/src/fantasy/waiver/startup_engine.py
    - backend/tests/test_startup_engine.py
requirements-completed: [FS-09]
duration: retroactive
completed: 2026-03-28
---

# 15-03 Summary

Completed the startup draft context engine for Phase 15.

- Implemented startup-mode detection from draft status and direction-to-template mapping through the shared build-template constants.
- Added build-template hints and per-pick trade-up/trade-down heuristics based on tier gaps and same-tier depth.
- Wired `StartupEngine.compute_context()` to read draft status, direction labels, and current pick values from the existing database tables.
- Added focused tests for startup detection, build-template assignment, and both trade heuristic paths.

Verification:

- `cd backend && .venv/bin/pytest tests/test_startup_engine.py -x -q`
