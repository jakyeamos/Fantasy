---
phase: 12-manager-rookie-pick-profiles
plan: "04"
subsystem: frontend
tags: [react, dossier, rookie-picks, ui]
requires:
  - phase: 12-02
    provides: rookie-pick profile fields on dossier responses
provides:
  - Rookie and pick-market dossier surfaces in overview and tabbed detail views
affects: [12-05, 12-06]
tech-stack:
  added: []
  patterns:
    - high-signal summary card on overview, full evidence drill-in behind a gated tab
    - dossier tabs stay contract-driven through explicit `show_draft_picks_tab` gating
key-files:
  created:
    - frontend/src/components/RookiePickMarketCard.tsx
    - frontend/src/components/DossierDraftPicksTab.tsx
  modified:
    - frontend/src/components/DossierOverviewTab.tsx
    - frontend/src/routes/league.$leagueId.managers.$managerId.tsx
    - frontend/src/api/types.ts
requirements-completed: [FS-06]
duration: retroactive
completed: 2026-03-27
---

# 12-04 Summary

Completed the dossier UI for rookie and pick-market profiling.

- Added `RookiePickMarketCard` to the overview tab so managers now show positional tendency, dominant archetype, and pick-market signal at a glance.
- Added `DossierDraftPicksTab` with pick-premium score detail, draft-selection history, and archetype-pattern breakdowns.
- Gated the new tab entirely behind `show_draft_picks_tab`, matching the low-evidence hiding rule from the phase design.
- Extended frontend profile types so the dossier route can consume the new backend fields safely.

Verification:

- `cd frontend && npx tsc --noEmit`

