---
phase: 12-manager-rookie-pick-profiles
plan: "05"
subsystem: frontend
tags: [manager-list, draft-room, warnings, react]
requires:
  - phase: 12-03
    provides: picks-buyer and manager-tendency signals on backend responses
  - phase: 12-04
    provides: dossier rookie-pick surfaces for end-to-end consistency
provides:
  - Quick-scan picks-buyer badge and draft-room manager-tendency surfacing
affects: []
tech-stack:
  added: []
  patterns:
    - existing warning render paths are reused instead of duplicating draft-room UI
key-files:
  created: []
  modified:
    - frontend/src/components/ManagerListRow.tsx
    - backend/src/fantasy/routers/draft_room.py
requirements-completed: [FS-06]
duration: retroactive
completed: 2026-03-27
---

# 12-05 Summary

Completed the remaining Phase 12 quick-scan surfaces.

- Added a `Picks Buyer` badge to manager rows when `pick_premium_score` is present at a meaningful level.
- Confirmed draft-room manager tendency warnings flow through the existing `TendencyWarningList` path once the backend includes `manager_tendency` entries.
- Preserved the silent-omission rule by leaving the badge fully absent when evidence is thin.

Deviation:

- No `frontend/src/routes/draft-room.tsx` change was required. The existing warning UI already rendered the new warning type once `backend/src/fantasy/routers/draft_room.py` appended it.

Verification:

- `backend/.venv/bin/python -m pytest backend/tests/rookie/test_draft_room.py -q`
- `cd frontend && npx tsc --noEmit`

