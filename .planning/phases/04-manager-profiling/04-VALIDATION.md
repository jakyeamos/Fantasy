---
phase: 4
slug: manager-profiling
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-21
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend), vitest (frontend) |
| **Config file** | `backend/pytest.ini` / `frontend/vitest.config.ts` |
| **Quick run command** | `cd backend && python -m pytest tests/test_profiling_engine.py tests/test_profiling_repo.py tests/test_profiling_router.py -x -q` |
| **Full suite command** | `cd backend && python -m pytest -x -q && cd ../frontend && npm run test -- --run` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/test_profiling_engine.py tests/test_profiling_repo.py tests/test_profiling_router.py -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest -x -q && cd ../frontend && npm run test -- --run`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 4-01-01 | 01 | 0 | MGR-01 | stub | `cd backend && python -m pytest tests/test_profiling_engine.py -x -q` | ❌ W0 | ⬜ pending |
| 4-01-02 | 01 | 0 | MGR-01 | stub | `cd backend && python -m pytest tests/test_profiling_repo.py -x -q` | ❌ W0 | ⬜ pending |
| 4-01-03 | 01 | 0 | MGR-01 | stub | `cd backend && python -m pytest tests/test_profiling_router.py -x -q` | ❌ W0 | ⬜ pending |
| 4-01-04 | 01 | 1 | MGR-01 | unit | `python -c "from fantasy.profiling.constants import MIN_TRADE_EVIDENCE_THRESHOLD; assert MIN_TRADE_EVIDENCE_THRESHOLD == 10"` | ❌ W0 | ⬜ pending |
| 4-01-05 | 01 | 1 | MGR-01 | unit | `cd backend && python -m pytest tests/test_profiling_engine.py::test_trade_filtering -x -q` | ❌ W0 | ⬜ pending |
| 4-01-06 | 01 | 1 | MGR-02 | unit | `cd backend && python -m pytest tests/test_profiling_engine.py::test_delta_computation -x -q` | ❌ W0 | ⬜ pending |
| 4-01-07 | 01 | 1 | MGR-02 | unit | `cd backend && python -m pytest tests/test_profiling_engine.py::test_exploitation_classification -x -q` | ❌ W0 | ⬜ pending |
| 4-01-08 | 01 | 1 | MGR-03 | unit | `cd backend && python -m pytest tests/test_profiling_engine.py::test_low_confidence_flag -x -q` | ❌ W0 | ⬜ pending |
| 4-01-09 | 01 | 1 | MGR-04 | unit | `cd backend && python -m pytest tests/test_profiling_engine.py::test_pitch_angle_generation -x -q` | ❌ W0 | ⬜ pending |
| 4-01-10 | 01 | 1 | MGR-01 | unit | `cd backend && python -m pytest tests/test_profiling_engine.py::test_missing_direction_graceful -x -q` | ❌ W0 | ⬜ pending |
| 4-01-11 | 01 | 1 | MGR-01 | integration | `cd backend && python -m alembic upgrade head` | ✅ | ⬜ pending |
| 4-02-01 | 02 | 1 | MGR-01 | integration | `cd backend && python -m pytest tests/test_profiling_repo.py::test_upsert_profile -x -q` | ❌ W0 | ⬜ pending |
| 4-02-02 | 02 | 1 | MGR-01 | integration | `cd backend && python -m pytest tests/test_profiling_repo.py::test_list_managers -x -q` | ❌ W0 | ⬜ pending |
| 4-02-03 | 02 | 1 | MGR-01 | integration | `cd backend && python -m pytest tests/test_profiling_router.py::test_managers_list_endpoint -x -q` | ❌ W0 | ⬜ pending |
| 4-02-04 | 02 | 1 | MGR-01 | integration | `cd backend && python -m pytest tests/test_profiling_router.py::test_manager_dossier_endpoint -x -q` | ❌ W0 | ⬜ pending |
| 4-02-05 | 02 | 1 | MGR-03 | integration | `cd backend && python -m pytest tests/test_profiling_router.py::test_compute_endpoint -x -q` | ❌ W0 | ⬜ pending |
| 4-03-01 | 03 | 2 | MGR-01 | e2e | `cd frontend && npm run test -- --run src/routes/managers` | ❌ W0 | ⬜ pending |
| 4-03-02 | 03 | 2 | MGR-02 | e2e | `cd frontend && npm run test -- --run src/routes/managers` | ❌ W0 | ⬜ pending |
| 4-03-03 | 03 | 2 | MGR-03 | visual | Manual — LOW CONFIDENCE amber banner visible | N/A | ⬜ pending |
| 4-03-04 | 03 | 2 | MGR-04 | visual | Manual — exploitation type labels visible per dossier | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_profiling_engine.py` — stubs for MGR-01, MGR-02, MGR-03, MGR-04 (trade filtering, delta computation, exploitation classification, pitch angle generation, low confidence flag, missing direction graceful handling)
- [ ] `backend/tests/test_profiling_repo.py` — stubs for MGR-01 (upsert_profile, upsert_pitch_angles, list_managers, get_profile)
- [ ] `backend/tests/test_profiling_router.py` — stubs for MGR-01, MGR-03 (managers_list, manager_dossier, compute endpoints)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| LOW CONFIDENCE amber banner renders for managers with < 10 trades | MGR-03 | Visual validation of amber color and evidence count display | Navigate to a manager dossier with known < 10 trade history. Confirm amber banner shows "LOW CONFIDENCE" with evidence count. Confirm no amber banner for managers with ≥ 10 trades. |
| Exploitation type label correct per manager | MGR-04 | Requires domain knowledge to validate classification accuracy | Review 2-3 known managers and verify exploitation_type matches their documented trade patterns (value-loss, timing-error, directionally-incoherent, archetype-overpayer). |
| Pitch angles render deal archetypes to accept/avoid | MGR-04 | Content validation — automated test cannot verify business logic accuracy | Open a dossier with > 10 trade evidence. Confirm pitch angles section shows at minimum 1 "accept" archetype and 1 "avoid" structure. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
