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
- [Phase 11]: Consolidation rows explicitly surface counterparty manager name and keep the Evaluate This Package CTA.
- [Phase 11]: Overview route keeps new lineup and hygiene panels roster-gated while preserving existing panel stack.
- [Phase 21]: `player_trends` is persisted through valuation write-through and read via a dedicated trends package.
- [Phase 21]: Opportunity ranking is gap magnitude first, confidence second; low-confidence opportunities still surface when the gap is large enough.
- [Phase 21]: Veteran decline signals can still convert to buy suggestions when the user has contender contexts on the board.
- [Frontend]: Player rankings ownership is actionable: owner names link to manager dossiers, and row-level trade evaluation links preserve league/active roster context while seeding the selected player into the correct trade bucket.
- [Refresh]: Manual league refresh now runs one full offseason pipeline: Sleeper ingest, FantasyCalc ADP refresh, 2026 actual draft-capital refresh, rookie-board rebuild, and artifact/snapshot recompute.
- [Refresh]: Manual league refresh and dev auto-refresh now update Edge Radar team context, dense player metadata freshness, player values/trends, waiver recommendation caches, manager profiles, and snapshots before `/opportunities` or Command Center reads cached side tables.
- [Refresh]: Actual draft-capital refresh marks both draft_capital and landing_spots freshness domains so rookie-board UI no longer serves stale offseason warnings after a successful manual refresh.
- [DuckDB]: Local FastAPI requests reuse one process-level DuckDB file connection to avoid same-process file-handle conflicts during post-refresh query invalidation.
- [Trade Evaluator]: The primary "You Receive" asset picker now scopes blank player search to the selected counterparty roster, so rostered players from that manager are browsable and evaluable again. Third-party receive buckets remain league-wide to preserve multi-team sidecar modeling.
- [Opportunity Feed]: Cards emit and render concrete CTAs. Buy/sell opportunities open the trade evaluator preseeded with league/user roster/player owner context when resolvable; hold/fallback opportunities route to manager dossiers or player rankings.
- [Market Gap Surfacing]: RookiePlayer and HygieneSuggestion responses now carry `model_vs_market_gap` from the shared recommendation-card market-gap engine, and the rookie board / hygiene rows reuse existing MarketGapPanel and MarketGapBadge components.
- [Local Startup]: `./dev.sh` is the primary local launcher. It blocks on `.venv/bin/alembic upgrade heads` from `backend/` before starting uvicorn, which covers both current 021 Alembic heads and keeps the workflow repo-local against `data/fantasy.duckdb`.
- [Trade Evaluator]: Multi-team trades now return `third_party_evaluations` with sidecar market fairness scores. Reroutes and package builder are no longer suppressed for multi-team requests when the primary counterparty path is otherwise evaluable.
- [Backend Verification]: `uv run pytest` from `backend/` now loads `pytest-asyncio` via the uv dev dependency group and passes 476 tests after baseline direction confidence/transition-contender calibration and DuckDB `player_trends` upsert timestamp repair.
- [Frontend Tokens]: Shared semantic UI tokens now cover success, warning, attention, info, strategy, destructive, season badges, shadows, label text sizes, and label tracking. Feature components consume `frontend/src/lib/ui-tokens.ts` instead of direct Tailwind palette/arbitrary color classes.
- [Edge Radar]: EdgeRadarEngine computes buy_low, buy_high, sell_high, sell_low, and waiver_pickup discoveries from player value vs market price deltas and cached waiver boards; CommandCenterEngine consumes the top discoveries as existing CommandAction rows.
- [Edge Radar]: Similarity evidence is first-class on player discoveries: same/similar position profiles are scored by age, value profile, team, and metadata-backed offensive system/head coach/offensive coordinator when present, then summarized with public weekly fantasy outcomes.
- [Edge Radar]: Similar-player evidence freshness now tracks global player_metadata and team_context domains, surfaces stale warnings in Opportunity Feed and Command Center, and exposes refresh actions for those evidence sources.
- [Edge Radar]: Curated dense player metadata now has a repo-owned default CSV at `data/edge_radar/player_dense_metadata.csv`; `/ingest/player-metadata/import-csv` imports that path when `csv_path` is omitted, and `python -m fantasy.edge_radar.player_metadata` provides the same local import path. The committed CSV is header-only until real sourced dense metrics are curated.
- [Edge Radar]: `player_dense_metadata` source health now requires one player row to include YPRR, route participation, snap share, and first-read share together before reporting ready.
- [Backend Verification]: `uv run pytest` from `backend/` passed 501 tests after Edge Radar discovery-layer integration.
- [Backend Verification]: `uv run pytest` from `backend/` passed 524 tests after refresh-pipeline Edge Radar source and downstream cache integration.
- [Code Quality]: Player backfill catalog degradation, pick class-strength fallback, and trade static pick valuation fallback now emit logging and response/domain metadata instead of silently changing recommendation quality.
- [Backend Verification]: `uv run pytest` from `backend/` passed 548 tests after surfacing refresh/pick/trade degradation metadata.
- [Frontend Verification]: `pnpm build` from `frontend/` passed after updating API response types for degradation metadata.
- [Backend Verification]: Focused Edge Radar/ingest verification passed 24 tests. After removing unsourced seed rows and clearing the local seed metadata import, local `python -m fantasy.edge_radar.player_metadata` imported 0/0 rows and Edge Radar source health reported `player_dense_metadata` missing, avoiding false readiness.
- [Backend Verification]: Full `uv run pytest` currently reports 551 passed and 1 unrelated deterministic failure in `tests/trends/test_opportunity_engine.py::test_buy_target_solving_lineup_gap_outranks_larger_raw_gap`.

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
