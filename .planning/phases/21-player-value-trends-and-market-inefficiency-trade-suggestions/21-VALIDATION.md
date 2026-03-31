---
phase: 21
slug: player-value-trends-and-market-inefficiency-trade-suggestions
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-31
---

# Phase 21 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `backend/pytest.ini` or `backend/pyproject.toml` |
| **Quick run command** | `cd backend && python -m pytest tests/trends/ -x -q` |
| **Full suite command** | `cd backend && python -m pytest -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/trends/ -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Block | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------|-----------|-------------------|-------------|--------|
| 21-01-01 | 01 | 1 | F | unit | `cd backend && python -m pytest tests/conftest.py -x -q` | ❌ W0 | ⬜ pending |
| 21-02-01 | 02 | 1 | A | unit | `cd backend && python -m pytest tests/trends/test_trend_engine.py -x -q` | ❌ W0 | ⬜ pending |
| 21-03-01 | 03 | 2 | B | unit | `cd backend && python -m pytest tests/trends/test_opportunity_engine.py -x -q` | ❌ W0 | ⬜ pending |
| 21-03-02 | 03 | 2 | C | unit | `cd backend && python -m pytest tests/trends/test_conflict_detection.py -x -q` | ❌ W0 | ⬜ pending |
| 21-04-01 | 04 | 2 | E | unit | `cd backend && python -m pytest tests/trends/test_anti_overreaction_weakening.py -x -q` | ❌ W0 | ⬜ pending |
| 21-04-02 | 04 | 2 | D | unit | `cd backend && python -m pytest tests/trends/test_trend_supporting_factor.py -x -q` | ❌ W0 | ⬜ pending |
| 21-05-01 | 05 | 3 | G | manual | See Manual-Only Verifications | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/trends/__init__.py` — package marker for trends test suite
- [ ] `backend/tests/trends/test_trend_engine.py` — stubs for Block A tests (7 tests)
- [ ] `backend/tests/trends/test_opportunity_engine.py` — stubs for Block B tests (9 tests)
- [ ] `backend/tests/trends/test_conflict_detection.py` — stubs for Block C tests (5 tests)
- [ ] `backend/tests/trends/test_trend_supporting_factor.py` — stubs for Block D tests (5 tests)
- [ ] `backend/tests/trends/test_anti_overreaction_weakening.py` — stubs for Block E tests (4 tests)
- [ ] `backend/tests/conftest.py` — add `player_trends` DDL to `SCHEMA_SQL` list

*Wave 0 creates stubs that fail; subsequent tasks implement the code to make them pass.*

---

## Manual-Only Verifications

| Behavior | Block | Why Manual | Test Instructions |
|----------|-------|------------|-------------------|
| `/opportunities` route renders `OpportunityFeedPage` | G | No frontend automated tests in this project | Navigate to `http://localhost:5173/opportunities` in browser; page renders without error |
| `TrendBadge` correct color per label | G | CSS/visual | `will_rise` → primary color; `will_fall` → destructive/red; `will_maintain` → accent/muted |
| `SuggestedActionBadge` correct color | G | CSS/visual | Same color scheme as `TrendBadge` |
| `ConflictExplanationPanel` visible by default | G | Interaction state | Amber container renders without clicking when `conflict_explanation` is non-null |
| `SimilarPlayersSection` collapsed by default | G | Interaction state | Section is collapsed on initial render; expands on chevron click |
| Dashboard link to `/opportunities` present | G | Visual regression | "View Opportunities" link present in Cross-League Exposure card footer |
| Dashboard stat tile shows opportunities count | G | Visual regression | Stat tile value matches `OpportunityFeedResponse.total` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING (❌ W0) references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
