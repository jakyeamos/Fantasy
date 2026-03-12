---
phase: 1
slug: sleeper-ingestion
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-12
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.23.x |
| **Config file** | `backend/pyproject.toml` — does not exist yet (Wave 0 installs) |
| **Quick run command** | `pytest backend/tests/ -x -q -k "not integration"` |
| **Full suite command** | `pytest backend/tests/ -v --tb=short` |
| **Estimated runtime** | ~30 seconds (unit-only); ~90 seconds (full suite) |

---

## Sampling Rate

- **After every task commit:** Run `pytest backend/tests/ -x -q -k "not integration"`
- **After every plan wave:** Run `pytest backend/tests/ -v --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds (unit), 90 seconds (full)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-W0-01 | W0 | 0 | All | setup | `pytest backend/tests/ -x -q --collect-only` | ❌ W0 | ⬜ pending |
| 1-01-01 | 01 | 1 | INGEST-01 | unit | `pytest backend/tests/test_sleeper_mapper.py::test_map_league_settings -x` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | INGEST-01 | unit | `pytest backend/tests/test_sleeper_mapper.py::test_flag_derivation -x` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 1 | INGEST-02 | unit | `pytest backend/tests/test_sleeper_mapper.py::test_map_roster -x` | ❌ W0 | ⬜ pending |
| 1-02-01 | 02 | 1 | INGEST-03 | unit | `pytest backend/tests/test_league_repo.py::test_upsert_standings -x` | ❌ W0 | ⬜ pending |
| 1-02-02 | 02 | 1 | INGEST-04 | unit | `pytest backend/tests/test_sleeper_mapper.py::test_map_traded_picks -x` | ❌ W0 | ⬜ pending |
| 1-03-01 | 03 | 2 | INGEST-05 | integration | `pytest backend/tests/test_ingest_service.py::test_trade_history_all_weeks -x` | ❌ W0 | ⬜ pending |
| 1-03-02 | 03 | 2 | INGEST-06 | integration | `pytest backend/tests/test_ingest_service.py::test_transactions_by_type -x` | ❌ W0 | ⬜ pending |
| 1-03-03 | 03 | 2 | All | integration | `pytest backend/tests/test_ingest_service.py::test_idempotent_ingest -x` | ❌ W0 | ⬜ pending |
| 1-04-01 | 04 | 2 | INGEST-07 | integration | `pytest backend/tests/test_corrections.py::test_correction_survives_reingest -x` | ❌ W0 | ⬜ pending |
| 1-05-01 | 05 | 3 | INGEST-08 | unit | `pytest backend/tests/test_gap_detector.py::test_gap_surfacing -x` | ❌ W0 | ⬜ pending |
| 1-05-02 | 05 | 3 | All | unit | `pytest backend/tests/test_sleeper_mapper.py::test_partial_response_handling -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/pyproject.toml` — pytest config, dependencies, `[tool.pytest.ini_options]` asyncio_mode = "auto"
- [ ] `backend/tests/__init__.py` — package marker
- [ ] `backend/tests/conftest.py` — shared fixtures: in-memory DuckDB connection, mock Sleeper API responses via pytest-httpx
- [ ] `backend/tests/test_sleeper_mapper.py` — stubs for INGEST-01, INGEST-02, INGEST-04; null-handling
- [ ] `backend/tests/test_league_repo.py` — stubs for INGEST-03; upsert idempotency
- [ ] `backend/tests/test_ingest_service.py` — stubs for INGEST-05, INGEST-06; full run integration
- [ ] `backend/tests/test_corrections.py` — stubs for INGEST-07
- [ ] `backend/tests/test_gap_detector.py` — stubs for INGEST-08
- [ ] Framework install: `pip install pytest pytest-asyncio pytest-httpx`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| League connect UI shows scoring/roster settings populated | INGEST-01 | Requires running frontend + real Sleeper league ID | Start app, enter a valid league ID, verify all format flags appear in UI |
| Data freshness dashboard shows gap labels with phase attribution | INGEST-08 | UI rendering of gap cards requires visual inspection | Ingest a partial league, check dashboard shows named gaps with "Expected resolution: Phase X" format |
| Manual correction persists in UI after re-ingest | INGEST-07 | End-to-end flow requires UI interaction | Edit a data point in UI, trigger re-ingest, verify correction is not overwritten |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
