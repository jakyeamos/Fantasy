---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: implementing
stopped_at: Phase 21 implementation complete
last_updated: "2026-06-12T21:43:42Z"
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
**Current focus:** Phase 21 — player value trends and market inefficiency trade suggestions

## Current Position

Phase: 21 (player-value-trends-and-market-inefficiency-trade-suggestions) — COMPLETE
Plan: 7 of 7

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

- Phase 21 added: player value trends and market inefficiency trade suggestions
- Phase 21 executed end to end: trend engine, opportunity feed route, opportunity feed UI, and dashboard entry points

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
- [Phase 11]: Consolidation rows explicitly surface counterparty manager name and keep the Evaluate This Package CTA.
- [Phase 11]: Overview route keeps new lineup and hygiene panels roster-gated while preserving existing panel stack.
- [Phase 21]: `player_trends` is persisted through valuation write-through and read via a dedicated trends package.
- [Phase 21]: Opportunity ranking is gap magnitude first, confidence second; low-confidence opportunities still surface when the gap is large enough.
- [Phase 21]: Veteran decline signals can still convert to buy suggestions when the user has contender contexts on the board.
- [Frontend]: Player rankings ownership is actionable: owner names link to manager dossiers, and row-level trade evaluation links preserve league/active roster context while seeding the selected player into the correct trade bucket.

### Pending Todos

- [Phase 9 scope]: Multi-team third-party trade scoring — TradeEngine does not score three-way trades; deferred to Phase 9. Trade evaluator counterparty asset picker only shows picks, not rostered players — counterparty player selection is broken. Both gaps should be addressed in Phase 9 planning.

### Blockers/Concerns

- [Phase 8]: Research is complete, but external dependencies (`scikit-learn`, `nflreadpy`, `scipy`) and the ETL/model pipeline are still the highest execution-risk area.
- [Schema]: Dual schema management — Alembic migrations (001–010) are not run at startup; `startup_tasks.py` manually adds only 2 columns as a compat shim; `conftest.py` has a third independent schema copy. Any new Phase 8/9 tables must be added in all three places or they will fail silently. Resolve before Phase 8 execution.
- [Schema]: No migration runner at startup — new users and phase deployments require `alembic upgrade head` manually; this step is not documented in the primary startup flow. Phase 8 adds 3 new tables that will not exist without it.
- [Code Quality]: Silent exception swallowing in `pick_engine._load_class_strength_signal`, `trade_engine._build_pick_proxy`, and `ingest_service._backfill_roster_players` — all use bare `except Exception: pass/return 0.0` with no logging. Failures are invisible in production.

## Session Continuity

Last session: 2026-03-31T16:05:01.243Z
Stopped at: Phase 21 implementation complete
Resume file: .planning/phases/21-player-value-trends-and-market-inefficiency-trade-suggestions/21-07-SUMMARY.md
