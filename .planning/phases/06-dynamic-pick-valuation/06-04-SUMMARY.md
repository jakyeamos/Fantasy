---
phase: 06-dynamic-pick-valuation
plan: "04"
subsystem: frontend
tags: [timing-badge, pick-context, league-pick-list]
requires:
  - phase: 06-03
    provides: `/picks` API and dynamic trade pick values
provides:
  - TimingBadge component and pick-aware AssetChip variant
  - PickValueSummaryRow inside trade evaluation output
  - LeaguePickList with recompute action on league detail
  - Trade evaluator wiring for demand-adjusted pick context
affects: [07-04]
tech-stack:
  added: []
  patterns:
    - query-keyed batch pick lookups reused across trade and league surfaces
    - player chip rendering preserved while pick chips expand into timing context
key-files:
  created:
    - frontend/src/components/picks/TimingBadge.tsx
    - frontend/src/components/picks/PickValueSummaryRow.tsx
    - frontend/src/components/picks/LeaguePickList.tsx
  modified:
    - frontend/src/components/trade/AssetChip.tsx
    - frontend/src/components/trade/EvaluationOutputPanel.tsx
    - frontend/src/routes/trades.tsx
    - frontend/src/routes/league.$leagueId.tsx
    - frontend/src/api/queries.ts
    - frontend/src/api/types.ts
requirements-completed: [PICK-01, PICK-02, PICK-03]
duration: retroactive
completed: 2026-03-22
---

# Phase 06-04: Dynamic Pick UI Summary

**Completed the Phase 6 frontend by surfacing timing recommendations and dynamic pick values in both the league drill-in and the trade evaluator.**

## Verification

- `npm run build` passes in `frontend/`
- League detail and trade routes compile with the new pick components
