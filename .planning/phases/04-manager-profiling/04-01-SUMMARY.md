---
phase: 04-manager-profiling
plan: "01"
subsystem: profiling
tags: [profiling, constants, models, alembic, repository]
requires:
  - phase: 03
    provides: direction labels and snapshots
provides:
  - Profiling package scaffold under backend/src/fantasy/profiling/
  - PITCH_ARCHETYPES, EXPLOITATION_TYPE_WEIGHTS, MIN_TRADE_EVIDENCE_THRESHOLD (=10), ADP_FALLBACK_BY_POSITION
  - Pydantic models: ManagerProfile, ManagerSummary, PitchAngle, ExploitationClassification
  - ProfilingRepo with upsert for manager_profiles, replace for manager_pitch_angles
  - Alembic migration 006 (manager_profiles, manager_pitch_angles tables)
affects: [04-02, 05]
tech-stack:
  added: []
  patterns: [MIN_TRADE_EVIDENCE_THRESHOLD as named constant — not magic number]
key-files:
  created:
    - backend/src/fantasy/profiling/constants.py
    - backend/src/fantasy/profiling/models.py
    - backend/src/fantasy/profiling/profiling_repo.py
    - backend/alembic/versions/006_phase4_profiling_tables.py
key-decisions:
  - "Evidence threshold (10 trades) stored as named constant MIN_TRADE_EVIDENCE_THRESHOLD"
  - "LOW confidence label required when evidence_count < threshold"
requirements-completed: [MGR-01, MGR-02, MGR-04]
duration: retroactive
completed: 2026-03-22
---

# Phase 04-01: Profiling Foundation Summary

**Profiling package scaffold, constants, models, ProfilingRepo, and migration 006.**
