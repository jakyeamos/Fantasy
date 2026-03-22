---
phase: 02-team-intelligence
plan: "04"
subsystem: api
tags: [intelligence-service, fastapi, lazy-compute]
requires:
  - phase: 02-03
    provides: all three engines
provides:
  - IntelligenceService orchestrating scorecard → direction → valuation
  - Lazy recompute on cache miss in get_* methods
  - Idempotent compute (same inputs produce same output, second call reuses cached result)
  - FastAPI /intelligence router with compute, scorecard, direction, player-value endpoints
affects: [03, 04, 05]
tech-stack:
  added: []
  patterns: [compute_league() as entry point, lazy recompute on get_* methods]
key-files:
  created:
    - backend/src/fantasy/intelligence/intelligence_service.py
    - backend/src/fantasy/routers/intelligence.py
  modified:
    - backend/src/fantasy/main.py
    - backend/tests/test_intelligence_service.py
    - backend/tests/test_intelligence_router.py
key-decisions:
  - "Idempotent compute — scorecard changes trigger direction recompute"
requirements-completed: [TEAM-01, TEAM-02, TEAM-03, TEAM-04, TEAM-05, PLAY-01, PLAY-02, PLAY-03, PLAY-04]
duration: retroactive
completed: 2026-03-22
---

# Phase 02-04: IntelligenceService + Router Summary

**Orchestration layer + HTTP API completing the intelligence pipeline.**
