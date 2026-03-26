---
phase: 14
slug: trust-infrastructure
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-26
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `backend/pytest.ini` or `backend/pyproject.toml` |
| **Quick run command** | `cd backend && python -m pytest tests/test_trust_scanner.py -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/test_trust_scanner.py -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 14-01-01 | 01 | 1 | FS-07 | unit | `pytest tests/test_trust_scanner.py -x -q` | ❌ W0 | ⬜ pending |
| 14-01-02 | 01 | 1 | FS-07 | unit | `pytest tests/test_trust_scanner.py -x -q` | ❌ W0 | ⬜ pending |
| 14-02-01 | 02 | 2 | FS-07 | integration | `pytest tests/test_trust_router.py -x -q` | ❌ W0 | ⬜ pending |
| 14-02-02 | 02 | 2 | FS-07 | integration | `pytest tests/test_trust_router.py -x -q` | ❌ W0 | ⬜ pending |
| 14-03-01 | 03 | 3 | FS-07 | manual | Browser: league page shows banner | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_trust_scanner.py` — stubs for all 11 scanner/confidence unit tests (tests 1–11)
- [ ] `backend/tests/test_trust_router.py` — stubs for router integration tests (tests 12–14)
- [ ] No new framework install required — pytest already present

*Wave 0 creates the test files with stub functions that fail; implementation waves make them pass.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Median-wins banner visible on league page after deployment | FS-07 | Requires real browser + live league data | Load `/league/{id}` for either connected league; verify `FormatWarningBanner` appears above panels |
| "I understand, continue" button dismisses banner + persists across reload | FS-07 | Requires browser interaction | Click dismiss; reload page; confirm banner does not reappear |
| Unsupported rule banner shows no dismiss button | FS-07 | Requires browser + test data | Simulate `best_ball=1` league in test DB; load page; confirm no "I understand" button |
| Banner absent for fully-supported league | FS-07 | Requires browser | Load league with only supported rules; confirm no banner renders |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
