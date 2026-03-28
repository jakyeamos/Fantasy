---
phase: 15
slug: waiver-startup-workflows
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `backend/pyproject.toml` |
| **Quick run command** | `cd backend && uv run pytest tests/test_waiver_engine.py tests/test_orphan_engine.py tests/test_startup_engine.py -x -q` |
| **Full suite command** | `cd backend && uv run pytest -x -q` |
| **Estimated runtime** | ~45 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest tests/test_waiver_engine.py tests/test_orphan_engine.py tests/test_startup_engine.py -x -q`
- **After every plan wave:** Run `cd backend && uv run pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 15-01-01 | 01 | 1 | FS-05 | unit | `uv run pytest tests/test_waiver_engine.py::test_faab_contender_bid -x -q` | ❌ W0 | ⬜ pending |
| 15-01-02 | 01 | 1 | FS-05 | unit | `uv run pytest tests/test_waiver_engine.py::test_faab_rebuild_bid -x -q` | ❌ W0 | ⬜ pending |
| 15-01-03 | 01 | 1 | FS-05 | unit | `uv run pytest tests/test_waiver_engine.py::test_free_agent_only_threshold -x -q` | ❌ W0 | ⬜ pending |
| 15-01-04 | 01 | 1 | FS-05 | unit | `uv run pytest tests/test_waiver_engine.py::test_bid_ceiling_enforcement -x -q` | ❌ W0 | ⬜ pending |
| 15-01-05 | 01 | 1 | FS-05 | unit | `uv run pytest tests/test_waiver_engine.py::test_zero_budget -x -q` | ❌ W0 | ⬜ pending |
| 15-01-06 | 01 | 1 | FS-05 | unit | `uv run pytest tests/test_waiver_engine.py::test_rolling_waiver_type -x -q` | ❌ W0 | ⬜ pending |
| 15-01-07 | 01 | 1 | FS-05 | unit | `uv run pytest tests/test_waiver_engine.py::test_free_agent_availability -x -q` | ❌ W0 | ⬜ pending |
| 15-01-08 | 01 | 1 | FS-05 | unit | `uv run pytest tests/test_waiver_engine.py::test_remaining_budget_calc -x -q` | ❌ W0 | ⬜ pending |
| 15-01-09 | 01 | 1 | FS-05 | unit | `uv run pytest tests/test_waiver_engine.py::test_stale_data_warning -x -q` | ❌ W0 | ⬜ pending |
| 15-02-01 | 02 | 1 | FS-09 | unit | `uv run pytest tests/test_startup_engine.py::test_startup_detection -x -q` | ❌ W0 | ⬜ pending |
| 15-02-02 | 02 | 1 | FS-09 | unit | `uv run pytest tests/test_startup_engine.py::test_build_template_assignment -x -q` | ❌ W0 | ⬜ pending |
| 15-02-03 | 02 | 1 | FS-09 | unit | `uv run pytest tests/test_startup_engine.py::test_trade_up_trigger -x -q` | ❌ W0 | ⬜ pending |
| 15-02-04 | 02 | 1 | FS-09 | unit | `uv run pytest tests/test_startup_engine.py::test_trade_down_trigger -x -q` | ❌ W0 | ⬜ pending |
| 15-03-01 | 03 | 2 | FS-05, FS-09 | unit | `uv run pytest tests/test_orphan_engine.py::test_age_curve_score -x -q` | ❌ W0 | ⬜ pending |
| 15-03-02 | 03 | 2 | FS-05, FS-09 | unit | `uv run pytest tests/test_orphan_engine.py::test_composite_score_range -x -q` | ❌ W0 | ⬜ pending |
| 15-03-03 | 03 | 2 | FS-05, FS-09 | unit | `uv run pytest tests/test_orphan_engine.py::test_action_plan_sort_order -x -q` | ❌ W0 | ⬜ pending |
| 15-04-01 | 04 | 3 | FS-05 | integration | `uv run pytest tests/integration/test_waiver_router.py -x -q` | ❌ W0 | ⬜ pending |
| 15-04-02 | 04 | 3 | FS-09 | integration | `uv run pytest tests/integration/test_startup_router.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_waiver_engine.py` — unit test stubs for FAAB bid range, free agent availability, FAAB state derivation (FS-05)
- [ ] `backend/tests/test_startup_engine.py` — unit test stubs for startup detection, build template assignment, trade-up/down heuristics (FS-09)
- [ ] `backend/tests/test_orphan_engine.py` — unit test stubs for orphan intake scoring and action plan generation (FS-05, FS-09)
- [ ] `backend/tests/integration/test_waiver_router.py` — integration test stubs for waiver recommendation and orphan-intake endpoints
- [ ] `backend/tests/integration/test_startup_router.py` — integration test stub for startup context endpoint
- [ ] `backend/tests/conftest.py` — extend with fixtures for waiver/startup/orphan tables (`waiver_recommendations`, `startup_contexts`, `orphan_intakes`, `action_plans`)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Stale data badge appears when hours_since_ingest > 12 | FS-05 | Requires UI inspection with mock ingest timestamp | Load waiver panel with `ingested_at` set to >12h ago; verify orange badge visible |
| Startup mode panels appear only when draft.status = pre_draft/drafting | FS-09 | Conditional render requires visual confirmation | Load league with draft.status="drafting"; verify startup panels render; set to "complete"; verify panels hidden |
| Orphan intake gated behind is_orphan toggle | FS-05 | Feature gate requires UI toggle interaction | Verify intake panel hidden by default; toggle on; verify panel appears |
| Bid range displays low/mid/high in monospace font | FS-05 | Typography requires visual inspection | Load waiver recommendations; verify three distinct values in `font-mono` |
| Action plan items sorted by urgency then priority | FS-05, FS-09 | Sort order requires visual confirmation across multiple items | Load action plan for distressed team; verify this_week items precede 30_days items |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
