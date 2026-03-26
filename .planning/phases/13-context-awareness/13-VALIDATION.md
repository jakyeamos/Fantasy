---
phase: 13
slug: context-awareness
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-26
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | backend/pytest.ini or pyproject.toml |
| **Quick run command** | `cd backend && python -m pytest tests/ -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/ -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 13-01-01 | 01 | 1 | FS-03 | unit | `cd backend && python -m pytest tests/test_calendar_state.py -x -q` | ❌ W0 | ⬜ pending |
| 13-01-02 | 01 | 1 | FS-03 | unit | `cd backend && python -m pytest tests/test_calendar_state.py -x -q` | ❌ W0 | ⬜ pending |
| 13-02-01 | 02 | 2 | FS-03 | unit | `cd backend && python -m pytest tests/test_calendar_state.py tests/test_scorecard_engine.py -x -q` | ❌ W0 | ⬜ pending |
| 13-03-01 | 03 | 2 | FS-08 | unit | `cd backend && python -m pytest tests/test_freshness.py -x -q` | ❌ W0 | ⬜ pending |
| 13-03-02 | 03 | 2 | FS-08 | unit | `cd backend && python -m pytest tests/test_freshness.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_calendar_state.py` — stubs for FS-03 (CalendarStateService, DynastyCalendarState enum)
- [ ] `backend/tests/test_freshness.py` — stubs for FS-08 (freshness domain tagging, stale-state warnings)
- [ ] Fixtures in `backend/tests/conftest.py` for mock league/player contexts

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Calendar state auto-selection matches current NFL date | FS-03 | Requires real calendar date context | Override to a known date, verify state label in recommendation output |
| Stale-state warnings visible on UI surfaces | FS-08 | Frontend rendering check | Load trade/pick recommendation, confirm staleness badge appears when data age > threshold |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
