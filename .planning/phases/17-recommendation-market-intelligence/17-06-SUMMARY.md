---
phase: 17-recommendation-market-intelligence
plan: "06"
subsystem: ui
tags: [trade-ui, lineup-ui, hygiene-ui, rookie-ui]
requires:
  - phase: 17-05
provides:
  - Recommendation-card surfaces across trade, lineup, and hygiene panels
  - Explicit TODO placeholders where per-row/per-prospect gap fields do not exist yet
key-files:
  modified:
    - frontend/src/components/trade/EvaluationOutputPanel.tsx
    - frontend/src/components/hygiene/HygieneSuggestionRow.tsx
    - frontend/src/components/hygiene/RosterHygienePanel.tsx
    - frontend/src/components/lineup/LineupStrengthCard.tsx
    - frontend/src/components/lineup/TitleWindowPanel.tsx
    - frontend/src/components/rookie/RookiePlayerCard.tsx
completed: 2026-03-31
---

# 17-06 Summary

Completed the initial UI integration for Phase 17 recommendation surfaces.

- Trade, lineup, and hygiene panels now render recommendation-card lists when Phase 17 data is present.
- The existing strategic-distinction banner remains in the trade panel during this migration step.
- Added TODO placeholders in `HygieneSuggestionRow` and `RookiePlayerCard` for future inline gap fields that are not yet on those per-item response types.

Verification:

- `cd frontend && ./node_modules/.bin/tsc --noEmit`
