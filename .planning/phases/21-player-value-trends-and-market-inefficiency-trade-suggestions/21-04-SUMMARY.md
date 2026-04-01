---
phase: 21-player-value-trends-and-market-inefficiency-trade-suggestions
plan: "04"
subsystem: backend
tags: [valuation, anti-overreaction, supporting-factors]
completed: 2026-03-31
---

# 21-04 Summary

- Extended `ValuationEngine.compute_player()` with optional trend-aware direction weakening for elite `will_fall` players.
- Added `trend_to_supporting_factor()` so Phase 21 trend output can slot into Phase 17-style supporting-factor contracts.
- Added direct regression coverage for elite/non-elite weakening cases and supporting-factor shape/direction rules.
