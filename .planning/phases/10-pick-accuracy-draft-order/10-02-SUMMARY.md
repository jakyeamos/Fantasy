# 10-02 Summary

Integrated draft-order rules into the pick engine and added the blocked-state contract.

- Refactored `expected_draft_slot()` in `backend/src/fantasy/picks/pick_engine.py` into rule-aware dispatch.
- Added `expected_draft_slot_inverse()`, `expected_draft_slot_max_pf()`, and `_build_rule_citation()`.
- Blocked all pick projections when no draft-order rule is configured by returning sentinel slot `1.0`, zeroed values, and `rule_citation=None`.
- Preserved citation rendering for configured leagues, including confirmed-slot picks.
- Optimized batch computation to load the draft-order rule once per league and max-PF slots once when needed.
- Extended pick-engine tests and pick-router integration tests for blocked and configured states.

Verification:

- `cd backend && .venv/bin/pytest tests/picks/test_pick_engine.py -q`
- `cd backend && .venv/bin/pytest tests/integration/test_pick_router.py -q`

