---
phase: 06-dynamic-pick-valuation
plan: "03"
subsystem: backend
tags: [fastapi, picks-router, trade-integration]
requires:
  - phase: 06-02
    provides: PickEngine dynamic valuation logic
provides:
  - `/picks` router with batch, single-pick, and recompute endpoints
  - FastAPI registration in main application
  - TradeRepo dynamic pick value redirect into PickEngine
  - Integration coverage for pick API flows
affects: [06-04, 07-03]
tech-stack:
  added: []
  patterns:
    - API reads compute live values; recompute persists snapshots to `pick_values`
    - Trade evaluation uses dynamic pick pricing rather than round baseline constants
key-files:
  created:
    - backend/src/fantasy/routers/picks.py
  modified:
    - backend/src/fantasy/main.py
    - backend/src/fantasy/trade/trade_repo.py
    - backend/src/fantasy/trade/trade_engine.py
    - backend/tests/integration/test_pick_router.py
requirements-completed: [PICK-01, PICK-02, PICK-03]
duration: retroactive
completed: 2026-03-22
---

# Phase 06-03: Picks API And Trade Integration Summary

**Exposed live pick valuation over FastAPI and redirected Phase 5 trade evaluation to the dynamic pick engine so pick packages now price against league state instead of static round baselines.**

## Verification

- `backend/tests/integration/test_pick_router.py` passes
- Full backend suite passes with the new router registration and trade integration
