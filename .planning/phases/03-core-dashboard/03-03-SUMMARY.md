---
phase: 03-core-dashboard
plan: "03"
subsystem: frontend
tags: [dashboard, league-card, risers-fallers, exploit-window, snapshot]
requires:
  - phase: 03-02
    provides: frontend scaffold
provides:
  - LeagueCard component for dashboard league grid
  - RisersFallersList component showing player value deltas
  - ExploitWindowPanel showing behavioral trigger cards
  - SnapshotStatus component showing time since last snapshot
  - Dashboard index route with league card list and ingest status
  - League detail route with direction label, confidence badge, risers/fallers, exploit windows
affects: [04, 05]
tech-stack:
  added: []
  patterns: [TanStack Query for data, real data everywhere (no stubs)]
key-files:
  created:
    - frontend/src/components/LeagueCard.tsx
    - frontend/src/components/RisersFallersList.tsx
    - frontend/src/components/ExploitWindowPanel.tsx
    - frontend/src/components/SnapshotStatus.tsx
  modified:
    - frontend/src/routes/index.tsx
    - frontend/src/routes/league.$leagueId.tsx
requirements-completed: [DASH-01, DASH-02, DASH-03, DASH-04]
duration: retroactive
completed: 2026-03-22
---

# Phase 03-03: Frontend Dashboard Views Summary

**League card grid, drill-in views with risers/fallers, exploit windows, and snapshot status.**

## Known Quality Gaps

- Cross-league exposure alerts remain placeholder copy on the dashboard index; no concentration-risk data is rendered yet.
- `SnapshotStatus` is reused on drill-in views, but "Snapshot now" still triggers a portfolio-wide snapshot rather than a league-scoped one.
