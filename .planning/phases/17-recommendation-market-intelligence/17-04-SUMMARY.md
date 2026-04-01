---
phase: 17-recommendation-market-intelligence
plan: "04"
subsystem: backend
tags: [trade, lineup, hygiene, waiver, persistence]
requires:
  - phase: 17-01
  - phase: 17-02
  - phase: 17-03
provides:
  - Recommendation-card fields on primary response models and engine-level card emission
affects: [17-05, 17-06]
key-files:
  modified:
    - backend/src/fantasy/trade/models.py
    - backend/src/fantasy/lineup/models.py
    - backend/src/fantasy/waiver/models.py
    - backend/src/fantasy/rookie/models.py
    - backend/src/fantasy/trade/trade_engine.py
    - backend/src/fantasy/lineup/lineup_engine.py
    - backend/src/fantasy/lineup/hygiene_engine.py
    - backend/src/fantasy/waiver/waiver_engine.py
    - backend/src/fantasy/intelligence/intelligence_service.py
    - backend/src/fantasy/lineup/lineup_repo.py
    - backend/tests/integration/test_recommendation_surfaces.py
completed: 2026-03-31
---

# 17-04 Summary

Completed the backend response retrofit and recommendation emission work.

- Added `recommendation_cards` to trade, lineup, hygiene, waiver, rookie-board, and draft-room models.
- Wired trade, lineup, hygiene, and waiver flows to emit populated recommendation cards and persist lineup/hygiene cards.
- Kept `TradeEvaluation.strategic_distinction` during this migration step for compatibility with the current UI/tests while adding the new card field alongside it.

Verification:

- `cd backend && ./.venv/bin/pytest tests/integration/test_recommendation_surfaces.py tests/intelligence/test_trade_engine.py tests/lineup/test_lineup_engine.py tests/lineup/test_hygiene_engine.py tests/integration/test_trade_router.py tests/integration/test_intelligence_router.py -q --tb=short`
