---
phase: 05-trade-intelligence
plan: "01"
subsystem: trade
tags: [trade, models, constants, repository]
requires:
  - phase: 02
    provides: player_values, team_directions
  - phase: 04
    provides: manager_profiles, pitch_angles
provides:
  - Trade package scaffold under backend/src/fantasy/trade/
  - PICK_MARKET_VALUES, MARKET_FAIR_THRESHOLD, DIRECTION_ADVANCING_THRESHOLD, MAX_REROUTES constants
  - Pydantic models: TradeAsset, TradeRequest, TradeEvaluation, DimensionScore, StrategicDistinction, RerouteResult, PackageOffer, PackageBuilderResult
  - TradeRepo with reads for player values, direction, manager profile, roster players, search
  - Test stubs for TradeEngine, PackageBuilder, RerouteEngine, trade router
affects: [05-02, 05-03, 05-04]
tech-stack:
  added: []
  patterns: [TradeRepo as single read boundary for all trade engine data needs]
key-files:
  created:
    - backend/src/fantasy/trade/constants.py
    - backend/src/fantasy/trade/models.py
    - backend/src/fantasy/trade/trade_repo.py
    - backend/tests/intelligence/test_trade_engine.py
    - backend/tests/intelligence/test_package_builder.py
    - backend/tests/intelligence/test_reroute_engine.py
    - backend/tests/integration/test_trade_router.py
requirements-completed: [TRADE-01, TRADE-04]
duration: retroactive
completed: 2026-03-22
---

# Phase 05-01: Trade Foundation Summary

**Trade package scaffold, constants, models, TradeRepo, and test stubs.**
