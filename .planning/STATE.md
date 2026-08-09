---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: implementing
stopped_at: Curated dense player metadata import path wired without unsourced seed data
last_updated: "2026-07-03T17:19:24-04:00"
progress:
  total_phases: 21
  completed_phases: 16
  total_plans: 83
  completed_plans: 77
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-11)

**Core value:** Tell me what my team is, what my best path is, who to trade with, what kind of deal to make, and whether the prospect or pick decision I'm considering is actually sharp in this format and league.
**Current focus:** Edge Radar discovery layer — backend-only normalized market-delta intelligence feeding Command Center actions, with no new primary frontend route.

## Current Position

Phase: Baseline stabilization
Plan: Edge Radar discovery layer

## Performance Metrics

**Velocity:**

- Total plans completed: 30
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
| Phase 06-dynamic-pick-valuation | 4 | 4 plans | backend + frontend complete |
| Phase 07-rookie-board-draft-room | 4 | 4 plans | backend + frontend complete |
| Phase 11 P01 | 88 | 3 tasks | 7 files |
| Phase 11 P02 | 1 min | 3 tasks | 10 files |
| Phase 11 P03 | 1 min | 2 tasks | 6 files |
| Phase 11 P04 | 2 min | 3 tasks | 3 files |

## Accumulated Context

### Roadmap Evolution

- 2026-07-04: Phase 22 planned: QR remediation: fantasy from QR run qr-fleet-continue-20260704-fantasy.
- Phase 21 added: player value trends and market inefficiency trade suggestions
- Phase 21 executed end to end: trend engine, opportunity feed route, opportunity feed UI, and dashboard entry points
- Edge Radar inserted as a backend discovery/intelligence layer after Phase 21 to rank opportunities by delta from public market and feed existing decision surfaces instead of creating another primary UX destination

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Roadmap: Python 3.12 / FastAPI / DuckDB / Polars backend; React 19 / Vite / TanStack Query / shadcn+ui frontend
- Roadmap: Adapter-first architecture — all Sleeper JSON parsing isolated in SleeperMapper; six engines consume only internal Pydantic domain models
- Roadmap: DuckDB chosen over SQLite — 10-17x faster for analytical query patterns; all schema DDL must target DuckDB 1.5.0, not SQLite
- [Phase 06-01]: Migration numbered 009 (not 007 as planned) because 007 and 008 already exist; picks package PickValuationContext uses TradeAsset for pick identity; Phase 7 class_strength_signal hook defaults to 0.0 with CLASS_STRENGTH_WEIGHT=0.20
- [Phase 06]: PickEngine, `/picks` router, dynamic TradeRepo integration, TimingBadge/LeaguePickList surfaces, and trade pick context are now live and fully verified
- [Phase 07]: Rookie board cache and league draft tendencies ship in migration 010; RookieEngine feeds class strength back into Phase 6; rookie board and draft room routes are live end to end
- [Phase 11]: Use Literal-based title-window and hygiene action type aliases for explicit API contracts.
- [Phase 11]: Maintain byte-aligned triple-write DDL across migration, startup schema compat, and test schema bootstrap.
- [Phase 11]: Persist lineup slot and hygiene suggestion payloads as compact deterministic JSON in LineupRepo.
- [Phase 11]: Lineup scoring normalizes starter slots across league to prevent lineup-length bias.
- [Phase 11]: Contender directions are post-adjusted only when title window is Outside Window via fragility boost.
- [Phase 11]: Hygiene output ordering is deterministic: consolidate, cut, stash, taxi.
- [Phase 11]: Kept title-window labels as strict literal unions in frontend types to mirror backend contracts.
- [Phase 11]: Used the DraftOrderRule-style summary/edit flow for TaxiConfigForm to maintain league settings UX consistency.

### Pending Todos

- [Phase 9 scope]: Remaining multi-team trade depth is offer construction across every participant; the current evaluator scores third-party sidecar legs and keeps primary-path reroutes/package builder enabled.

### Blockers/Concerns

- [Phase 8]: Research is complete, but external dependencies (`scikit-learn`, `nflreadpy`, `scipy`) and the ETL/model pipeline are still the highest execution-risk area.
- [Schema]: Dual schema management remains for tests/runtime compatibility (`startup_tasks.py` plus `conftest.py`), but the normal local launcher now runs Alembic before backend boot. Direct `uvicorn` usage still requires a manual `alembic upgrade heads`.
- [Code Quality]: `command_center.py` is over the local changed-line readiness size gate (656 nonblank lines after Edge Radar adapter wiring). The adapter is small, but the file should be split by action lane before further Command Center expansion.

## Session Continuity

Last session: 2026-06-29T20:54:31-04:00
Stopped at: Silent fallback degradation metadata surfaced and verified with `uv run pytest` plus `pnpm build`
Resume file: .planning/STATE.md
