---
phase: 06-dynamic-pick-valuation
plan: "02"
subsystem: backend
tags: [pick-engine, valuation, timing, demand-signals]
requires:
  - phase: 06-01
    provides: picks package foundation, constants, models, PickRepo contracts
provides:
  - PickEngine with batch and single-pick valuation flows
  - Standings-aware slot projection and future-year discount handling
  - Timing recommendations with reasoning strings
  - Class-strength hook that stays neutral at 0.0 and can load Phase 7 output when available
affects: [06-03, 06-04, 07-03]
tech-stack:
  added: []
  patterns:
    - lazy class-strength load from rookie cache or RookieEngine
    - pure helper functions for slot math, timing, and rebuilder premium
key-files:
  created:
    - backend/src/fantasy/picks/pick_engine.py
  modified:
    - backend/tests/picks/test_pick_engine.py
requirements-completed: [PICK-01, PICK-02, PICK-03]
duration: retroactive
completed: 2026-03-22
---

# Phase 06-02: Pick Engine Summary

**Implemented the Phase 6 valuation engine with standings projection, calendar timing, class-strength integration hooks, rebuilder demand adjustment, and future-pick discounting.**

## Verification

- `backend/tests/picks/test_pick_engine.py` passes
- Full backend suite passes with Phase 6 engine active
