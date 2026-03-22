---
phase: 02-team-intelligence
plan: "01"
subsystem: intelligence
tags: [scorecard, normalization, corrections]
requires:
  - phase: 02-00
    provides: models, constants, output tables
provides:
  - ScorecardEngine computing 9 raw dimension scores per roster
  - League-wide normalization so scores are relative within each league
  - Corrections application at compute time via _apply_corrections()
  - Missing stats defaults and fragility availability proxy
affects: [02-02, 02-03, 02-04, 04, 05]
tech-stack:
  added: []
  patterns: [pure compute engine — reads from DB inputs, returns TeamScorecard dicts]
key-files:
  created:
    - backend/src/fantasy/intelligence/scorecard_engine.py
  modified:
    - backend/tests/test_scorecard_engine.py
key-decisions:
  - "Corrections applied in-memory at compute time, not at ingest time"
  - "All 9 scores normalized within league so they are relative, not absolute"
requirements-completed: [TEAM-01]
duration: retroactive
completed: 2026-03-22
---

# Phase 02-01: ScorecardEngine Summary

**9-dimension team scoring with league-wide normalization and in-memory corrections application.**

## Known Quality Gaps

- `_score_positional_insulation()` checks `starter_position in bench_positions` (a list, O(n)) — does not correctly account for duplicate positions in bench; can undercount insulation
- `_score_pick_capital()` can double-count a pick that was traded away and received back in certain scenarios
