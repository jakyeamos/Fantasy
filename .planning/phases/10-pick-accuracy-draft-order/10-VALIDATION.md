---
phase: 10
slug: pick-accuracy-draft-order
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `backend/pyproject.toml` |
| **Quick run command** | `cd backend && python -m pytest tests/picks/ -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/picks/ -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | FS-01 | unit | `cd backend && python -m pytest tests/picks/test_draft_order_rule.py -x -q` | ❌ W0 | ⬜ pending |
| 10-01-02 | 01 | 1 | FS-01 | unit | `cd backend && python -m pytest tests/picks/test_draft_order_rule.py -x -q` | ❌ W0 | ⬜ pending |
| 10-01-03 | 01 | 1 | FS-01 | unit | `cd backend && python -m pytest tests/picks/test_draft_order_rule.py -x -q` | ❌ W0 | ⬜ pending |
| 10-02-01 | 02 | 2 | FS-01 | unit | `cd backend && python -m pytest tests/picks/test_pick_engine_dispatch.py -x -q` | ❌ W0 | ⬜ pending |
| 10-02-02 | 02 | 2 | FS-01 | unit | `cd backend && python -m pytest tests/picks/test_pick_engine_dispatch.py -x -q` | ❌ W0 | ⬜ pending |
| 10-03-01 | 03 | 2 | FS-01 | regression | `cd backend && python -m pytest tests/picks/test_draft_order_fixtures.py -x -q` | ❌ W0 | ⬜ pending |
| 10-03-02 | 03 | 2 | FS-01 | regression | `cd backend && python -m pytest tests/picks/test_draft_order_fixtures.py -x -q` | ❌ W0 | ⬜ pending |
| 10-04-01 | 04 | 3 | FS-01 | manual | Visual inspection of DraftOrderRuleForm in league settings | — | ⬜ pending |
| 10-04-02 | 04 | 3 | FS-01 | manual | Visual inspection of RuleCitation on all pick surfaces | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/picks/test_draft_order_rule.py` — stubs for DB model, CRUD, and API endpoint tasks
- [ ] `backend/tests/picks/test_pick_engine_dispatch.py` — stubs for dispatcher, blocked state, citation rendering
- [ ] `backend/tests/picks/test_draft_order_fixtures.py` — regression fixture stubs for inverse standings, max PF, and playoff ordering scenarios
- [ ] `backend/tests/conftest.py` — ensure `league_draft_order_rules` table is in `SCHEMA_SQL` (triple-management requirement)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| DraftOrderRuleForm renders correctly in league settings | FS-01 | React component visual inspection | Navigate to a league, open settings, confirm all three fields render; confirm Save button is disabled until all fields filled |
| RuleCitation appears on all pick surfaces | FS-01 | Cross-surface visual scan | Check trade evaluator, picks list, and draft room — each must show citation text or "Rule not configured" placeholder |
| Clicking citation or placeholder navigates to league settings | FS-01 | Browser interaction test | Click citation text — confirm navigation to `league.$leagueId` with `#draft-order-rule` hash scroll |
| Confirmed-slot picks show citation | FS-01 | Visual inspection | A confirmed 1.01 pick must still show rule citation, not a blank citation field |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
