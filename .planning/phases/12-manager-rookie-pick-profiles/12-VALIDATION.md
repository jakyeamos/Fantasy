---
phase: 12
slug: manager-rookie-pick-profiles
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-25
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) · vitest (frontend) |
| **Config file** | `backend/pyproject.toml` · `frontend/vite.config.ts` |
| **Quick run command** | `cd backend && uv run pytest tests/picks/ tests/integration/ -x -q` |
| **Full suite command** | `cd backend && uv run pytest -x -q && cd ../frontend && npm test -- --run` |
| **Estimated runtime** | ~30 seconds (backend) · ~15 seconds (frontend) |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest tests/picks/ tests/integration/ -x -q`
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 12-01-00 | 01 | 0 | FS-06 | unit stub | `uv run pytest tests/picks/test_rookie_pick_repo.py tests/picks/test_package_builder_integration.py tests/picks/test_reroute_picks_buyer.py --collect-only -q` | ❌ W0 | ⬜ pending |
| 12-01-01 | 01 | 0 | FS-06 | unit stub | `uv run pytest tests/picks/test_rookie_pick_repo.py -x -q` | ❌ W0 | ⬜ pending |
| 12-02-01 | 02 | 1 | FS-06 | unit | `uv run pytest tests/picks/test_rookie_pick_engine.py -x -q` | ❌ W0 | ⬜ pending |
| 12-02-02 | 02 | 1 | FS-06 | unit | `uv run pytest tests/picks/test_rookie_pick_engine.py::test_pick_premium_scoring -x -q` | ❌ W0 | ⬜ pending |
| 12-03-01 | 03 | 1 | FS-06 | integration | `uv run pytest tests/integration/test_pick_router.py -x -q` | ✅ | ⬜ pending |
| 12-03-02 | 03 | 2 | FS-06 | integration | `uv run pytest tests/integration/test_pick_router.py::test_draft_pick_ingest -x -q` | ❌ W0 | ⬜ pending |
| 12-03-03 | 03 | 2 | FS-06 | unit stub | `uv run pytest tests/picks/test_package_builder_integration.py -x -q` | ❌ W0 | ⬜ pending |
| 12-03-04 | 03 | 2 | FS-06 | unit stub | `uv run pytest tests/picks/test_reroute_picks_buyer.py -x -q` | ❌ W0 | ⬜ pending |
| 12-04-01 | 04 | 2 | FS-06 | unit | `uv run pytest tests/picks/test_rookie_pick_engine.py::test_evidence_threshold -x -q` | ❌ W0 | ⬜ pending |
| 12-04-02 | 04 | 2 | FS-06 | unit | `uv run pytest tests/picks/test_rookie_pick_engine.py::test_silent_omission -x -q` | ❌ W0 | ⬜ pending |
| 12-05-01 | 05 | 2 | FS-06 | unit | `uv run pytest tests/picks/test_package_builder_integration.py -x -q` | ❌ W0 | ⬜ pending |
| 12-05-02 | 05 | 2 | FS-06 | unit | `uv run pytest tests/picks/test_reroute_picks_buyer.py -x -q` | ❌ W0 | ⬜ pending |
| 12-06-01 | 06 | 3 | FS-06 | manual | See manual verifications below | N/A | ⬜ pending |
| 12-06-02 | 06 | 3 | FS-06 | manual | See manual verifications below | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/picks/test_rookie_pick_repo.py` — stubs for FS-06 repo upsert, schema integrity (created by Plan 01 Task 0)
- [ ] `backend/tests/picks/test_package_builder_integration.py` — stubs for FS-06 tiered package builder logic (created by Plan 01 Task 0)
- [ ] `backend/tests/picks/test_reroute_picks_buyer.py` — stubs for FS-06 picks_buyer reroute type (created by Plan 01 Task 0)
- [ ] `backend/tests/picks/test_rookie_pick_engine.py` — full unit tests created by Plan 02 Task 1 (TDD)
- [ ] `backend/tests/integration/test_pick_router.py` — extend existing file with draft pick ingest endpoint stubs

*Existing `backend/tests/integration/test_pick_router.py` already exists — extend, do not replace.*

*`test_rookie_pick_engine.py` is created with full TDD tests in Plan 02, not as a stub.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| "Draft & Picks" tab hidden when below evidence threshold | FS-06 (D-02) | Requires a seeded league with thin evidence; threshold toggling not automatable in unit context | Seed a manager with 2 pick-trade transactions (below `MIN_ROOKIE_PICK_EVIDENCE=5`). Navigate to dossier. Confirm 4th tab does not appear in the tab list. |
| "Picks Buyer" badge absent when evidence thin | FS-06 (D-17) | Same evidence threshold condition; requires visual confirmation of badge absence | With same thin-evidence manager, check ManagerListRow — confirm no badge rendered (not muted, fully absent). |
| Draft room manager tendency warning renders | FS-06 (D-05/D-06) | Requires draft room session with seeded league data; end-to-end UI flow | Start a mock draft session for a league where a manager has positional tendency signal. Confirm `TendencyWarning` row appears with `warning_type="manager_tendency"` value. |
| Package builder structural change (pick included) | FS-06 (D-15) | Requires counterparty with above-threshold pick-premium score in a trade evaluation context | Evaluate a trade where counterparty has sufficient pick-premium evidence. Confirm the package suggestion includes a pick asset in the offer structure (not just reasoning text). |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
