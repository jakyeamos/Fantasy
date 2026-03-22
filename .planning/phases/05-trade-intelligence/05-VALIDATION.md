---
phase: 5
slug: trade-intelligence
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-21
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `backend/pytest.ini` or `backend/pyproject.toml` |
| **Quick run command** | `cd backend && python -m pytest tests/intelligence/ -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/intelligence/ -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-00 | 01 | 0 | TRADE-01 | stub | `cd backend && python -m pytest tests/intelligence/ tests/integration/ -x -q` | Created W0 | ⬜ pending |
| 05-01-01 | 01 | 0 | TRADE-01 | import | `cd backend && python -c "from fantasy.trade.constants import DIMENSION_WEIGHTS"` | N/A | ⬜ pending |
| 05-01-02 | 01 | 0 | TRADE-01 | import | `cd backend && python -c "from fantasy.trade.trade_repo import TradeRepo"` | N/A | ⬜ pending |
| 05-02-01 | 02 | 1 | TRADE-01 | unit | `cd backend && python -m pytest tests/intelligence/test_trade_engine.py -x -q` | ✅ W0 | ⬜ pending |
| 05-02-02 | 02 | 1 | TRADE-02,03 | integration | `cd backend && python -m pytest tests/integration/test_trade_router.py -x -q` | ✅ W0 | ⬜ pending |
| 05-02-03 | 02 | 1 | TRADE-02,03 | unit | `cd backend && python -m pytest tests/intelligence/test_reroute_engine.py tests/intelligence/test_package_builder.py -x -q` | ✅ W0 | ⬜ pending |
| 05-03-01 | 03 | 1 | TRADE-01 | tsc | `cd frontend && npx tsc --noEmit` | N/A | ⬜ pending |
| 05-04-01 | 04 | 2 | TRADE-01 | e2e | manual — UI interaction | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `backend/tests/intelligence/test_trade_engine.py` — stubs for TRADE-01, TRADE-02 (Plan 01 Task 0)
- [x] `backend/tests/intelligence/test_package_builder.py` — stubs for TRADE-03, TRADE-04 (Plan 01 Task 0)
- [x] `backend/tests/intelligence/test_reroute_engine.py` — stubs for TRADE-02 (Plan 01 Task 0)
- [x] `backend/tests/integration/test_trade_router.py` — stub for /trade API endpoint (Plan 01 Task 0)
- [x] `backend/tests/intelligence/__init__.py` — package init (Plan 01 Task 0)
- [x] `backend/tests/integration/__init__.py` — package init (Plan 01 Task 0)

*All Wave 0 stubs created by Plan 01 Task 0.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Trade evaluation UI renders correctly with 7 dimension scores | TRADE-01 | Visual rendering, shadcn component structure | Navigate to trade evaluation page, input a test trade, verify all 7 dimension scores appear with confidence labels |
| Strategic banner distinguishes market-fair vs strategically advancing | TRADE-04 | Contextual label logic, visual prominence | Input a market-fair but strategically neutral trade; verify banner does NOT show "strategically advancing" |
| Manager-specific opening offer generated in package builder | TRADE-03 | Requires manager_profiles data in DB | Input a desired acquisition, verify manager-specific offer appears and references exploit angle |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 20s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved (revision pass)
