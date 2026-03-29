---
phase: 17
slug: recommendation-market-intelligence
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `backend/pyproject.toml` |
| **Quick run command** | `cd backend && uv run pytest tests/ -x -q --tb=short` |
| **Full suite command** | `cd backend && uv run pytest tests/ -q --tb=short` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest tests/ -x -q --tb=short`
- **After every plan wave:** Run `cd backend && uv run pytest tests/ -q --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 17-01-01 | 01 | 1 | REC-01, REC-02 | unit | `cd backend && uv run pytest tests/test_recommendation_card.py -x -q` | ❌ W0 | ⬜ pending |
| 17-01-02 | 01 | 1 | REC-04 | unit | `cd backend && uv run pytest tests/test_recommendation_card.py::test_priority_rank -x -q` | ❌ W0 | ⬜ pending |
| 17-01-03 | 01 | 1 | REC-03 | unit | `cd backend && uv run pytest tests/test_recommendation_card.py::test_confidence_contract -x -q` | ❌ W0 | ⬜ pending |
| 17-02-01 | 02 | 1 | REC-05 | unit | `cd backend && uv run pytest tests/test_anti_overreaction.py -x -q` | ❌ W0 | ⬜ pending |
| 17-02-02 | 02 | 1 | REC-06 | unit | `cd backend && uv run pytest tests/test_flag_engine.py -x -q` | ❌ W0 | ⬜ pending |
| 17-03-01 | 03 | 2 | MKT-01 | unit | `cd backend && uv run pytest tests/test_market_gap.py -x -q` | ❌ W0 | ⬜ pending |
| 17-03-02 | 03 | 2 | MKT-02, MKT-03 | unit | `cd backend && uv run pytest tests/test_market_gap.py::test_gap_classification -x -q` | ❌ W0 | ⬜ pending |
| 17-04-01 | 04 | 2 | MKT-04 | integration | `cd backend && uv run pytest tests/integration/test_recommendation_surfaces.py -x -q` | ❌ W0 | ⬜ pending |
| 17-04-02 | 04 | 2 | MKT-05 | integration | `cd backend && uv run pytest tests/integration/test_recommendation_surfaces.py::test_hold_despite_weak_market -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_recommendation_card.py` — stubs for REC-01, REC-02, REC-03, REC-04
- [ ] `backend/tests/test_anti_overreaction.py` — stubs for REC-05 (elite composite, bearish/bullish dampening)
- [ ] `backend/tests/test_flag_engine.py` — stubs for REC-06 (depth chart, injury, expiry)
- [ ] `backend/tests/test_market_gap.py` — stubs for MKT-01, MKT-02, MKT-03
- [ ] `backend/tests/integration/test_recommendation_surfaces.py` — stubs for MKT-04, MKT-05

*Existing `conftest.py` and DuckDB fixture infrastructure can be reused from prior phases.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| FantasyCalc live API integration | MKT-01 | Requires live HTTP call to external service; mocked in unit tests | After migration 021 applied, run ingest and verify `lens_market` differs from model-derived value for at least one player |
| Coaching/QB change flags | REC-06 | Sleeper API does not expose typed coaching change events; proxied via `team_change` | After ingest cycle with a known team change, verify `team_change` flag appears on affected player cards |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
