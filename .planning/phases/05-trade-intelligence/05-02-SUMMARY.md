---
phase: 05-trade-intelligence
plan: "02"
subsystem: trade
tags: [trade-engine, reroute-engine, package-builder, fastapi]
requires:
  - phase: 05-01
    provides: models, constants, TradeRepo
provides:
  - TradeEngine scoring 7 dimensions (market_fairness, roster_fit, direction_fit, timing_quality, insulation_delta, liquidity_delta, manager_exploit_quality)
  - StrategicDistinction verdict (advancing/negative/neutral)
  - RerouteEngine generating up to 3 reroute suggestions (better target, cheaper send)
  - PackageBuilder generating Aggressive Open and Fair Close offers
  - FastAPI /trade router (evaluate, player search, pick search)
affects: [05-03, 05-04, 06]
tech-stack:
  added: []
  patterns: [manager profile absence degrades to LOW confidence, not error]
key-files:
  created:
    - backend/src/fantasy/trade/trade_engine.py
    - backend/src/fantasy/trade/reroute_engine.py
    - backend/src/fantasy/trade/package_builder.py
    - backend/src/fantasy/routers/trade.py
  modified:
    - backend/src/fantasy/main.py
    - backend/tests/intelligence/test_trade_engine.py
    - backend/tests/intelligence/test_reroute_engine.py
    - backend/tests/intelligence/test_package_builder.py
    - backend/tests/integration/test_trade_router.py
key-decisions:
  - "MAX_REROUTES = 3; up to 2 better targets + 1 cheaper send alternative"
  - "manager_profile absence → LOW confidence, not error"
requirements-completed: [TRADE-01, TRADE-02, TRADE-03, TRADE-04]
duration: retroactive
completed: 2026-03-22
---

# Phase 05-02: TradeEngine + Engines + Router Summary

**7-dimension trade evaluation, reroute suggestions, package builder, and HTTP API.**

## Known Quality Gaps

- Multi-team third-party trade legs (`third_party_trades`) now reduce confidence and annotate reasoning across the 7 dimensions. Numeric scoring still anchors to the user's net swap and primary counterparty, and reroutes/package generation are intentionally suppressed for multi-team deals.
- Roster ID/league ID cross-validation not performed — mismatched pair silently returns degraded results
