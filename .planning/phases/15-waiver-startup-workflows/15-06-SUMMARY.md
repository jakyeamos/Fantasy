---
phase: 15-waiver-startup-workflows
plan: "06"
subsystem: frontend
tags: [react, tanstack-query, routes, ui]
requires:
  - phase: 15-05
    provides: backend endpoints for waiver, startup, and orphan workflows
provides:
  - User-facing Phase 15 surfaces for waivers, startup drafts, and orphan intake
affects: []
tech-stack:
  added: []
  patterns:
    - feature routes compose small presentational panels over shared query contracts
    - league detail navigation exposes workflow tabs only within the existing drill-in shell
key-files:
  created:
    - frontend/src/routes/league.$leagueId.waivers.tsx
    - frontend/src/routes/league.$leagueId.startup.tsx
    - frontend/src/routes/league.$leagueId.orphan-intake.tsx
    - frontend/src/components/waivers/WaiverIntelHeader.tsx
    - frontend/src/components/waivers/WaiverPlayerList.tsx
    - frontend/src/components/waivers/WaiverPlayerRow.tsx
    - frontend/src/components/startup/StartupDraftContextCard.tsx
    - frontend/src/components/startup/StartupPickValuationList.tsx
    - frontend/src/components/startup/StartupBuildTemplatePanel.tsx
    - frontend/src/components/orphan/OrphanIntakeStatusCard.tsx
    - frontend/src/components/orphan/AgeCurveRiskPanel.tsx
    - frontend/src/components/orphan/PickCapitalPanel.tsx
    - frontend/src/components/orphan/DeadRosterPanel.tsx
    - frontend/src/components/orphan/LineupViabilityPanel.tsx
    - frontend/src/components/orphan/LiquidationOptionsPanel.tsx
    - frontend/src/components/orphan/ThirtyDayActionPlanCard.tsx
  modified:
    - frontend/src/api/types.ts
    - frontend/src/api/queries.ts
    - frontend/src/routes/league.$leagueId.tsx
requirements-completed: [FS-05, FS-09]
duration: retroactive
completed: 2026-03-28
---

# 15-06 Summary

Completed the frontend surfaces for Phase 15.

- Added typed query contracts for waiver recommendations, startup context, orphan intake, and action plans.
- Added new league-detail tabs and routes for Waivers, Startup Draft, and Orphan Intake.
- Built the waiver, startup, and orphan panel sets needed to render the new workflows inside the existing app shell.
- Regenerated the route tree and verified the frontend build against the new screens.

Verification:

- `cd frontend && npm run build`
