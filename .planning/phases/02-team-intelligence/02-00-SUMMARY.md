---
phase: 02-team-intelligence
plan: "00"
subsystem: intelligence
tags: [scorecard, direction, valuation, pydantic, alembic]
requires:
  - phase: 01
    provides: ingestion pipeline and player data
provides:
  - Intelligence package scaffold under backend/src/fantasy/intelligence/
  - Pydantic models: TeamScorecard, DirectionResult, PlayerValue, ScorecardInputs
  - Constants: DIRECTION_WEIGHTS, DIRECTION_MOVE_MATRIX, POSITIONAL_PEAK_AGE, ROUND_WEIGHTS, FORMAT_MULTIPLIERS
  - Alembic migration 004 (team_scorecards, team_directions, player_values output tables)
  - Test stubs for all Phase 2 modules
affects: [02-01, 02-02, 02-03, 02-04, 04, 05]
tech-stack:
  added: []
  patterns: [output tables separated from ingestion tables, engine inputs from ScorecardInputs model]
key-files:
  created:
    - backend/src/fantasy/intelligence/constants.py
    - backend/src/fantasy/intelligence/models.py
    - backend/alembic/versions/004_phase2_output_tables.py
key-decisions:
  - "Intelligence output stored in separate output tables — scorecards, directions, player values"
  - "ScorecardInputs aggregates all DB reads before engine computation — engines are pure functions"
requirements-completed: [TEAM-01, TEAM-02, TEAM-03, TEAM-04, TEAM-05, PLAY-01, PLAY-02, PLAY-03]
duration: retroactive
completed: 2026-03-22
---

# Phase 02-00: Intelligence Scaffold Summary

**Intelligence package models, constants, output table migrations, and test stubs.**
