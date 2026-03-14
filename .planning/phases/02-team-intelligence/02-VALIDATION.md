---
phase: 2
slug: team-intelligence
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pytest.ini or pyproject.toml (Phase 1 established) |
| **Quick run command** | `pytest tests/phase2/ -x -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/phase2/ -x -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 | 1 | TEAM-01 | unit | `pytest tests/phase2/test_scorecard.py -x -q` | ❌ W0 | ⬜ pending |
| 2-01-02 | 01 | 1 | TEAM-01 | unit | `pytest tests/phase2/test_scorecard.py -x -q` | ❌ W0 | ⬜ pending |
| 2-02-01 | 02 | 1 | TEAM-02/03 | unit | `pytest tests/phase2/test_direction.py -x -q` | ❌ W0 | ⬜ pending |
| 2-02-02 | 02 | 1 | TEAM-04/05 | unit | `pytest tests/phase2/test_direction.py -x -q` | ❌ W0 | ⬜ pending |
| 2-03-01 | 03 | 2 | PLAY-01/02 | unit | `pytest tests/phase2/test_player_value.py -x -q` | ❌ W0 | ⬜ pending |
| 2-03-02 | 03 | 2 | PLAY-03/04 | unit | `pytest tests/phase2/test_player_value.py -x -q` | ❌ W0 | ⬜ pending |
| 2-04-01 | 04 | 3 | TEAM-01..05 | integration | `pytest tests/phase2/test_api.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/phase2/__init__.py` — package marker
- [ ] `tests/phase2/test_scorecard.py` — stubs for TEAM-01
- [ ] `tests/phase2/test_direction.py` — stubs for TEAM-02, TEAM-03, TEAM-04, TEAM-05
- [ ] `tests/phase2/test_player_value.py` — stubs for PLAY-01, PLAY-02, PLAY-03, PLAY-04
- [ ] `tests/phase2/test_api.py` — integration stubs for FastAPI endpoints
- [ ] `tests/phase2/conftest.py` — shared fixtures (synthetic roster, DuckDB in-memory DB)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Direction weight vector calibration feels correct | TEAM-02 | Subjective judgment — weight constants are hypothesis, not ground truth | Review direction output against 5 synthetic rosters of known archetypes; confirm labels match intuition |
| Scorecard sub-scores sum to coherent team picture | TEAM-01 | Holistic judgment across 9 dimensions | Review a full scorecard for a "true contender" roster vs. a "hard rebuild" roster; verify sub-scores align |
| "What would change this label" reasoning is useful | TEAM-03 | Usefulness is subjective | Check 3 teams' delta explanations for clarity and actionability |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
