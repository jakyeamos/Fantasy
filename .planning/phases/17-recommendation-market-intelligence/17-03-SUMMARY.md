---
phase: 17-recommendation-market-intelligence
plan: "03"
subsystem: backend
tags: [market-data, fantasycalc, valuation, gap-engine]
requires:
  - phase: 17-01
  - phase: 17-02
provides:
  - Market service, FantasyCalc client, gap classification engine, and valuation-market retrofit
affects: [17-04, 17-05, 17-06]
key-files:
  created:
    - backend/src/fantasy/market/__init__.py
    - backend/src/fantasy/market/models.py
    - backend/src/fantasy/market/fantasycalc_client.py
    - backend/src/fantasy/market/market_service.py
    - backend/src/fantasy/recommendation/gap_engine.py
    - backend/tests/test_market_gap.py
  modified:
    - backend/src/fantasy/intelligence/valuation_engine.py
    - backend/alembic/versions/021_recommendation_phase.py
    - backend/src/fantasy/startup_tasks.py
    - backend/tests/conftest.py
completed: 2026-03-31
---

# 17-03 Summary

Completed the market-value and gap-classification layer.

- Added the FantasyCalc client and local `MarketService` with neutral fallbacks when external rows are absent.
- Retrofitted `ValuationEngine.lens_market` to use the Phase 17 market blend instead of the old model-only proxy.
- Added `MarketGapEngine` and tests for buy-low, sell-high, hold-despite-weak-market, and fallback behavior.

Verification:

- `cd backend && ./.venv/bin/pytest tests/test_market_gap.py tests/test_valuation_engine.py -q --tb=short`
