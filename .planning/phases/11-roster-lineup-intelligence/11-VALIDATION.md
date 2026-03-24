---
phase: 11
slug: roster-lineup-intelligence
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) |
| **Config file** | `backend/pyproject.toml` |
| **Quick run command** | `cd backend && pytest tests/intelligence/ tests/integration/test_intelligence_router.py tests/integration/test_taxi_config_router.py -x -q` |
| **Full suite command** | `cd backend && pytest tests/ -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && pytest tests/intelligence/ tests/integration/test_intelligence_router.py tests/integration/test_taxi_config_router.py -x -q`
- **After every plan wave:** Run `cd backend && pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 0 | FS-02 | unit | `cd backend && pytest tests/ -x -q` | ❌ W0 | ⬜ pending |
| 11-01-02 | 01 | 1 | FS-02 | unit | `cd backend && pytest tests/intelligence/test_lineup_engine.py -x -q` | ❌ W0 | ⬜ pending |
| 11-01-03 | 01 | 1 | FS-02 | unit | `cd backend && pytest tests/intelligence/test_title_window.py -x -q` | ❌ W0 | ⬜ pending |
| 11-02-01 | 02 | 1 | FS-04 | unit | `cd backend && pytest tests/intelligence/test_hygiene_engine.py -x -q` | ❌ W0 | ⬜ pending |
| 11-02-02 | 02 | 1 | FS-04 | integration | `cd backend && pytest tests/integration/test_taxi_config_router.py -x -q` | ❌ W0 | ⬜ pending |
| 11-03-01 | 03 | 2 | FS-02 | integration | `cd backend && pytest tests/integration/test_intelligence_router.py -x -q` | ❌ W0 | ⬜ pending |
| 11-04-01 | 04 | 2 | FS-02, FS-04 | TypeScript | `cd frontend && npx tsc --noEmit` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/intelligence/test_lineup_engine.py` — stubs for FS-02 (replacement level, title-window)
- [ ] `backend/tests/intelligence/test_title_window.py` — stubs for FS-02 (3-label classification, direction adjustment)
- [ ] `backend/tests/intelligence/test_hygiene_engine.py` — stubs for FS-04 (cut, consolidate, stash, taxi)
- [ ] `backend/tests/integration/test_taxi_config_router.py` — stubs for FS-04 (GET null, PUT save, GET returns saved)
- [ ] `backend/tests/conftest.py` — add `league_taxi_configs`, `lineup_scores`, `hygiene_suggestions` DDL to `SCHEMA_SQL`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| TitleWindowPanel badge renders in correct color per label | FS-02 | No frontend test framework | Load team screen; verify "Peak Window" shows accent badge, "Fading Window" shows primary badge, "Outside Window" shows muted badge |
| RosterHygienePanel consolidation suggestion names specific counterparty | FS-04 | Requires seeded league data with multiple rosters | Seed a league; load hygiene panel; verify "consolidate" suggestion shows `counterparty_name` and specific player names |
| Taxi config form saves and stale lineup data refreshes | FS-04 | Requires browser interaction + query invalidation | Change taxi config; verify lineup and hygiene panels re-fetch (network tab shows new requests) |
| Direction label nudge: "Outside Window" contender → fragile_contender | FS-02 | Requires controlled league seed with known scorecard values | Seed a high win_now + low ceiling roster; verify direction label is `fragile_contender`, not `true_contender` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
