---
phase: 04-manager-profiling
plan: "02"
subsystem: profiling
tags: [profiling-engine, exploitation-classification, pitch-angles, fastapi]
requires:
  - phase: 04-01
    provides: models, constants, ProfilingRepo
provides:
  - ProfilingEngine with full exploitation classification (value_loss, timing_error, directional_incoherence, archetype_overpay)
  - Primary/secondary exploitation type with threshold logic
  - Exploitability score in [0,1] range
  - Pitch angle selection using PITCH_ARCHETYPES
  - compute_all_profiles() for full league analysis
  - FastAPI /profiling router (compute, list managers, get manager)
affects: [04-03, 04-04, 05]
tech-stack:
  added: []
  patterns: [trade history parsed from transactions table, exploitation typed and evidenced]
key-files:
  created:
    - backend/src/fantasy/profiling/profiling_engine.py
    - backend/src/fantasy/routers/profiling.py
  modified:
    - backend/src/fantasy/main.py
    - backend/tests/test_profiling_engine.py
key-decisions:
  - "ProfilingEngine consumes trade history from transactions table — no separate trade storage"
requirements-completed: [MGR-01, MGR-02, MGR-03, MGR-04]
duration: retroactive
completed: 2026-03-22
---

# Phase 04-02: ProfilingEngine + Router Summary

**Full exploitation classification, exploitability scoring, pitch angles, and HTTP API.**
