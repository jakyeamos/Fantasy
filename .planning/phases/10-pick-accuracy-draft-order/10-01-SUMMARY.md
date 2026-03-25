# 10-01 Summary

Completed the Phase 10 backend foundation for league-specific draft-order rules.

- Added `NonPlayoffOrderBasis`, `PlayoffOrdering`, and `DraftTiebreaker` in `backend/src/fantasy/picks/constants.py`.
- Added `LeagueDraftOrderRule`, `PickValuationContext.draft_order_rule`, and `PickValue.rule_citation` in `backend/src/fantasy/picks/models.py`.
- Added `PickRepo.get_draft_order_rule()`, `save_draft_order_rule()`, and `get_max_pf_slots()` in `backend/src/fantasy/picks/pick_repo.py`.
- Added GET/PUT `/picks/{league_id}/draft-order-rule` endpoints in `backend/src/fantasy/routers/picks.py`.
- Added `league_draft_order_rules` to runtime schema compat and test schema.
- Created Alembic migration `backend/alembic/versions/013_draft_order_rules.py`.

Notes:

- The plan expected migration `012`, but this repo already contained `012_retrospective_runs.py`, so the new migration was correctly numbered `013`.

Verification:

- `cd backend && .venv/bin/pytest tests/picks/test_pick_repo.py -q`

