---
phase: 12-manager-rookie-pick-profiles
plan: "02"
subsystem: api
tags: [profiling, rookie-picks, ingest, fastapi]
requires:
  - phase: 12-01
    provides: rookie-pick schema, repo, and draft-pick mapper foundation
provides:
  - Rookie-pick profile scoring and on-demand draft-pick ingestion
affects: [12-03, 12-04, 12-05, 12-06]
tech-stack:
  added: []
  patterns:
    - behavioral scoring stays in engine code while routers merge outputs into existing profile contracts
    - on-demand draft-pick ingest remains separate from the default ingest flow
key-files:
  created:
    - backend/src/fantasy/rookie_pick/rookie_pick_engine.py
    - backend/tests/picks/test_rookie_pick_engine.py
  modified:
    - backend/src/fantasy/profiling/models.py
    - backend/src/fantasy/routers/profiling.py
    - backend/src/fantasy/ingestion/ingest_service.py
requirements-completed: [FS-06]
duration: retroactive
completed: 2026-03-27
---

# 12-02 Summary

Completed the engine layer that scores rookie-pick behavior and exposes it through profiling APIs.

- Added `RookiePickProfileEngine` with pick-premium scoring, positional tendency analysis, archetype pattern rollups, and evidence gating for the draft-picks tab.
- Extended `ManagerProfile` so dossier responses can carry rookie/pick profile fields without breaking existing profiling flows.
- Added `POST /profiling/leagues/{league_id}/ingest/draft-picks` for on-demand draft-pick ingestion.
- Hooked draft-pick ingestion into `IngestService` as a separate step that enriches selections and computes manager rookie-pick profiles.

Verification:

- `backend/.venv/bin/python -m pytest backend/tests/picks/test_rookie_pick_engine.py backend/tests/test_profiling_router.py backend/tests/test_profiling_engine.py -q`

