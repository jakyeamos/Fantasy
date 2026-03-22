---
phase: 02-team-intelligence
plan: "02"
subsystem: intelligence
tags: [direction, classification, confidence, delta]
requires:
  - phase: 02-00
    provides: models, constants
provides:
  - DirectionEngine classifying TeamScorecard into one of 8 direction labels
  - Confidence score, alternates, delta (sensitivity analysis), reasoning string, ranked moves
  - Weighted dot-product classification via DIRECTION_WEIGHTS
  - DIRECTION_MOVE_MATRIX completeness validated in tests
affects: [02-04, 03, 04, 05]
tech-stack:
  added: []
  patterns: [pure function — TeamScorecard in, DirectionResult out]
key-files:
  created:
    - backend/src/fantasy/intelligence/direction_engine.py
  modified:
    - backend/tests/test_direction_engine.py
key-decisions:
  - "8 direction labels: true_contender, contender, transition, true_rebuild, rebuild, asset_accumulator, pick_heavy, unknown"
  - "Delta computed as sensitivity analysis — how much would score need to change to flip label"
requirements-completed: [TEAM-02, TEAM-03, TEAM-04, TEAM-05]
duration: retroactive
completed: 2026-03-22
---

# Phase 02-02: DirectionEngine Summary

**8-label direction classification with confidence, alternates, delta, reasoning, and ranked moves.**
