---
phase: 21-player-value-trends-and-market-inefficiency-trade-suggestions
plan: "03"
subsystem: backend
tags: [opportunities, similarity, conflict-detection, calendar]
completed: 2026-03-31
---

# 21-03 Summary

- Added `find_similar_players()` and `OpportunityEngine.build_feed()` for the cross-league opportunity surface.
- Implemented impact-score ranking, ownership deduplication, conflict explanations, contender-aware veteran buy-low logic, and calendar escalation flags.
- Reused portfolio ownership logic with a safe roster fallback so the feed still works when portfolio-owner env settings are absent from the active DB.
