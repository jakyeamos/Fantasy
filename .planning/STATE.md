---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: implementing
stopped_at: Backend baseline pytest repaired after trend-result work
last_updated: "2026-06-28T10:41:59-04:00"
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
**Current focus:** Backend baseline verification after trend-result work — full backend `uv run pytest` passes with async test plugins available in the uv dev group, direction classification calibrated, and DuckDB trend upserts using a supported timestamp expression.

## Current Position

Phase: Baseline stabilization
Plan: Repair backend pytest failures after trend-result changes

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
- [Refresh]: Manual league refresh now runs one full offseason pipeline: Sleeper ingest, FantasyCalc ADP refresh, 2026 actual draft-capital refresh, rookie-board rebuild, and artifact/snapshot recompute.
- [Refresh]: Actual draft-capital refresh marks both draft_capital and landing_spots freshness domains so rookie-board UI no longer serves stale offseason warnings after a successful manual refresh.
- [DuckDB]: Local FastAPI requests reuse one process-level DuckDB file connection to avoid same-process file-handle conflicts during post-refresh query invalidation.
- [Trade Evaluator]: The primary "You Receive" asset picker now scopes blank player search to the selected counterparty roster, so rostered players from that manager are browsable and evaluable again. Third-party receive buckets remain league-wide to preserve multi-team sidecar modeling.
- [Opportunity Feed]: Cards emit and render concrete CTAs. Buy/sell opportunities open the trade evaluator preseeded with league/user roster/player owner context when resolvable; hold/fallback opportunities route to manager dossiers or player rankings.
- [Market Gap Surfacing]: RookiePlayer and HygieneSuggestion responses now carry `model_vs_market_gap` from the shared recommendation-card market-gap engine, and the rookie board / hygiene rows reuse existing MarketGapPanel and MarketGapBadge components.
- [Local Startup]: `./dev.sh` is the primary local launcher. It blocks on `.venv/bin/alembic upgrade heads` from `backend/` before starting uvicorn, which covers both current 021 Alembic heads and keeps the workflow repo-local against `data/fantasy.duckdb`.
- [Trade Evaluator]: Multi-team trades now return `third_party_evaluations` with sidecar market fairness scores. Reroutes and package builder are no longer suppressed for multi-team requests when the primary counterparty path is otherwise evaluable.
- [Backend Verification]: `uv run pytest` from `backend/` now loads `pytest-asyncio` via the uv dev dependency group and passes 476 tests after baseline direction confidence/transition-contender calibration and DuckDB `player_trends` upsert timestamp repair.

### Pending Todos

- [Phase 9 scope]: Remaining multi-team trade depth is offer construction across every participant; the current evaluator scores third-party sidecar legs and keeps primary-path reroutes/package builder enabled.

### Blockers/Concerns

- [Phase 8]: Research is complete, but external dependencies (`scikit-learn`, `nflreadpy`, `scipy`) and the ETL/model pipeline are still the highest execution-risk area.
- [Schema]: Dual schema management remains for tests/runtime compatibility (`startup_tasks.py` plus `conftest.py`), but the normal local launcher now runs Alembic before backend boot. Direct `uvicorn` usage still requires a manual `alembic upgrade heads`.
- [Code Quality]: Silent exception swallowing in `pick_engine._load_class_strength_signal`, `trade_engine._build_pick_proxy`, and `ingest_service._backfill_roster_players` — all use bare `except Exception: pass/return 0.0` with no logging. Failures are invisible in production.

## Session Continuity

Last session: 2026-06-28T10:41:59-04:00
Stopped at: Backend baseline pytest repaired and verified
Resume file: .planning/STATE.md
