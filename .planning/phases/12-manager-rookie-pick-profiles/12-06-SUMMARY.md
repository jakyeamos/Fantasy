---
phase: 12-manager-rookie-pick-profiles
plan: "06"
subsystem: profiling
tags: [manager-dossier, behavioral-fields, profiling, react]
requires:
  - phase: 12-02
    provides: rookie-pick scoring and extended profile responses
  - phase: 12-04
    provides: dossier rookie-pick UI structure
provides:
  - Manager Dossier 2.0 behavioral fields and exploit-map overview layout
affects: [13-03, 13-04]
tech-stack:
  added: []
  patterns:
    - behavioral trade guidance is computed server-side and rendered as a compact exploit map
    - dossier overview prioritizes actionable send/target guidance ahead of descriptive profile content
key-files:
  created:
    - backend/tests/profiling/test_behavioral_fields.py
  modified:
    - backend/src/fantasy/profiling/models.py
    - backend/src/fantasy/profiling/profiling_engine.py
    - backend/src/fantasy/routers/profiling.py
    - frontend/src/components/DossierOverviewTab.tsx
    - frontend/src/routes/league.$leagueId.managers.$managerId.tsx
    - frontend/src/api/types.ts
requirements-completed: [MGR2-01, MGR2-02, MGR2-03, MGR2-04]
duration: retroactive
completed: 2026-03-27
---

# 12-06 Summary

Completed Manager Dossier 2.0 on top of the rookie-pick profiling work.

- Added the new behavioral fields: motivations, urgency, calendar sensitivity, veteran appetite, rookie-fever index, value rigidity, reroute susceptibility, and best send/target assets.
- Extended `ProfilingEngine` to derive those fields from existing trade-history evidence without adding new tables.
- Reworked the dossier overview so the exploit map and trade guidance lead the screen instead of the older profile-first layout.
- Kept the low-confidence warning behavior intact when evidence stays below the existing trade threshold.

Verification:

- `backend/.venv/bin/python -m pytest backend/tests/profiling/test_behavioral_fields.py backend/tests/test_profiling_router.py backend/tests/test_profiling_engine.py -q`
- `cd frontend && npx tsc --noEmit`

