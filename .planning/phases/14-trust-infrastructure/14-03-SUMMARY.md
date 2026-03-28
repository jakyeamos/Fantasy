---
phase: 14-trust-infrastructure
plan: "03"
subsystem: frontend
tags: [react, tanstack-query, trust, warning-banner]
requires:
  - phase: 14-02
    provides: trust endpoints and durable acknowledgment state
provides:
  - Frontend trust endpoint contracts and query helpers
  - League overview warning banner for partial and unsupported formats
affects: [league-overview]
tech-stack:
  added: []
  patterns:
    - query-driven banner rendering with acknowledgment invalidation through TanStack Query
    - separate visual treatments for unsupported vs. partially supported formats
key-files:
  created:
    - frontend/src/components/FormatWarningBanner.tsx
  modified:
    - frontend/src/api/types.ts
    - frontend/src/api/queries.ts
    - frontend/src/routes/league.$leagueId.tsx
requirements-completed: [FS-07]
duration: retroactive
completed: 2026-03-28
---

# 14-03 Summary

Completed the user-facing trust warning surface.

- Added typed frontend contracts for trust scan and acknowledgment responses.
- Added trust query helpers and the acknowledgment mutation for the new backend endpoints.
- Added `FormatWarningBanner` with separate rendering paths for unsupported rules and partially supported rules.
- Wired the banner into the league overview so affected leagues surface trust warnings in the app.

Task Commits

1. `479fc6d` — `feat: add trust warning banner`

Verification:

- `cd frontend && npm run build`
