---
phase: 12-manager-rookie-pick-profiles
plan: "03"
subsystem: api
tags: [trade, reroute, package-builder, draft-room]
requires:
  - phase: 12-01
    provides: rookie-pick profile storage and constants
  - phase: 12-02
    provides: computed pick-premium and draft-tendency signals
provides:
  - Picks-buyer reroutes, pick-aware package builder logic, and manager draft-room warnings
affects: [12-05]
tech-stack:
  added: []
  patterns:
    - low-confidence rookie-pick signals are omitted silently on trade surfaces
    - manager tendency warnings reuse the existing draft-room warning shape
key-files:
  created: []
  modified:
    - backend/src/fantasy/trade/models.py
    - backend/src/fantasy/trade/reroute_engine.py
    - backend/src/fantasy/trade/package_builder.py
    - backend/src/fantasy/rookie/models.py
    - backend/src/fantasy/routers/draft_room.py
requirements-completed: [FS-06]
duration: retroactive
completed: 2026-03-27
---

# 12-03 Summary

Completed the Phase 12 backend integrations that make rookie-pick tendencies actionable in trade and draft flows.

- Added `picks_buyer` as a first-class reroute type and generated it when counterparties show meaningful pick-premium behavior.
- Taught the package builder to bias aggressive structures toward including picks when counterparty evidence is strong enough.
- Extended `TendencyWarning` with `manager_tendency` support and appended manager-specific warnings in the draft-room response.
- Kept low-confidence rookie/pick signals out of trade outputs instead of surfacing noisy qualifiers.

Verification:

- `backend/.venv/bin/python -m pytest backend/tests/picks/test_package_builder_integration.py backend/tests/picks/test_reroute_picks_buyer.py backend/tests/rookie/test_draft_room.py -q`

