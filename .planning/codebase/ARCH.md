# Codebase Architecture and Implementation Audit

**Analysis Date:** 2026-03-22

---

## Project Overview

Fantasy is a dynasty fantasy football intelligence platform. It ingests league data from Sleeper, computes roster scorecards and team direction labels, profiles manager trading behavior, evaluates trades across seven dimensions, and surfaces exploit windows. It consists of a Python/FastAPI backend and a React/TypeScript frontend.

---

## Full File Inventory

### Backend — Source (`backend/src/fantasy/`)

| File | Module | What It Does |
|------|--------|--------------|
| `main.py` | App | Creates FastAPI app, registers all routers, loads ADP baseline on startup via lifespan hook |
| `config.py` | Config | Pydantic `Settings` with `DB_PATH` and `INGEST_LOCK_TIMEOUT`; resolves absolute db path from repo root |
| `db/connection.py` | Database | `get_write_connection()` and `get_read_connection()` using DuckDB; read-only mode for reads |
| `db/models.py` | Database | SQLAlchemy `Table` definitions for all 10 core tables (leagues, rosters, standings, traded_picks, transactions, players, ingest_runs, corrections, player_stats_weekly, player_adp_baseline) |
| `ingestion/sleeper_client.py` | Ingestion | Async HTTP client for Sleeper API (`/league`, `/rosters`, `/traded_picks`, `/transactions/{week}`, `/state/nfl`, `/players/nfl`); retry on 429/5xx with exponential backoff via tenacity |
| `ingestion/sleeper_mapper.py` | Ingestion | Maps raw Sleeper API payloads to typed `LeagueSettings`, `RosterRow`, `StandingRow`, `TradedPickRow`, `TransactionRow` dataclasses |
| `ingestion/ingest_service.py` | Ingestion | Orchestrates a full ingest run: fetches league/rosters/picks/transactions → applies corrections → detects data gaps → writes snapshot; supports `full` and `incremental` run types; tracks run status in `ingest_runs` table |
| `ingestion/nfl_data_loader.py` | Ingestion | Loads weekly stats from `nfl_data_py`; maps Sleeper scoring keys to nflverse column names; loads ADP baseline from CSV; computes fantasy points per player/week |
| `ingestion/gap_detector.py` | Ingestion | Three static detectors: unmapped scoring keys, missing season stats, incomplete transaction cursor; returned as `DataGap` models attached to ingest run |
| `corrections/override_service.py` | Corrections | CRUD for the `corrections` table; `apply_corrections()` logs applied corrections (does not mutate live tables directly — corrections are consumed by `ScorecardEngine._apply_corrections()` at compute time) |
| `repositories/league_repo.py` | Repository | Upsert methods for leagues, rosters, standings, traded picks, transactions; backed by DuckDB raw SQL |
| `intelligence/models.py` | Intelligence | Pydantic models: `TeamScorecard` (9 normalized scores + composite), `DirectionResult` (label, confidence, reasoning, alternates, delta, moves), `PlayerValue` (12 components + 5 lenses), `ScorecardInputs` |
| `intelligence/constants.py` | Intelligence | Lookup tables: `DIRECTION_WEIGHTS`, `DIRECTION_MOVE_MATRIX`, `MOVE_TYPE_TARGETS`, `DIRECTION_VALUE_WEIGHTS`, `POSITIONAL_PEAK_AGE`, `POSITIONAL_CLIFF_AGE`, `ROUND_WEIGHTS`, `FORMAT_MULTIPLIERS` |
| `intelligence/scorecard_engine.py` | Intelligence | Computes 9 raw dimension scores per roster → normalizes within league → returns `dict[int, TeamScorecard]`; reads from DB for player stats, picks, ADP, corrections |
| `intelligence/direction_engine.py` | Intelligence | Pure computation: classifies `TeamScorecard` into one of 8 direction labels using weighted dot-product; computes confidence, alternates, delta (sensitivity analysis), reasoning string, ranked moves |
| `intelligence/valuation_engine.py` | Intelligence | Per-player computation of 12 components and 5 lenses using PPG, games played, age-curve, ADP, format multipliers; `compute_all()` iterates full roster |
| `intelligence/intelligence_service.py` | Intelligence | Orchestrates scorecard → direction → valuation; persists all three to DB tables; lazy-recomputes on cache miss in `get_*` methods |
| `profiling/models.py` | Profiling | Pydantic models: `ManagerProfile`, `ManagerSummary`, `PitchAngle`, `ExploitationClassification` |
| `profiling/constants.py` | Profiling | `PITCH_ARCHETYPES`, `EXPLOITATION_TYPE_WEIGHTS`, `SECONDARY_TYPE_THRESHOLD_RATIO`, `ADP_FALLBACK_BY_POSITION`, `PICK_VALUE_NORMALIZED`, `MIN_TRADE_EVIDENCE_THRESHOLD` |
| `profiling/profiling_engine.py` | Profiling | Full manager analysis: loads trade history → classifies exploitation type (value_loss, timing_error, directional_incoherence, archetype_overpay) → computes exploitability score → selects pitch angles; `compute_all_profiles()` for full league |
| `profiling/profiling_repo.py` | Profiling | Upsert `manager_profiles`, replace `manager_pitch_angles`; `get_profile()`, `list_manager_summaries()`, `get_pitch_angles()` |
| `trade/models.py` | Trade | Pydantic models: `TradeAsset`, `TradeRequest`, `TradeEvaluation`, `DimensionScore`, `StrategicDistinction`, `RerouteResult`, `PackageOffer`, `PackageBuilderResult`, `PlayerSearchResult`, `PickSearchResult` |
| `trade/constants.py` | Trade | `PICK_MARKET_VALUES`, `MARKET_FAIR_THRESHOLD`, `DIRECTION_ADVANCING_THRESHOLD`, `DIRECTION_NEGATIVE_THRESHOLD`, `MAX_REROUTES` |
| `trade/trade_repo.py` | Trade | DB reads for trade evaluation: `get_player_values()`, `get_team_direction()`, `get_manager_profile()`, `get_roster_players()`, `search_players()`, `get_picks_for_league()` |
| `trade/trade_engine.py` | Trade | Core trade evaluator: resolves asset values from DB → scores 7 dimensions (market_fairness, roster_fit, direction_fit, timing_quality, insulation_delta, liquidity_delta, manager_exploit_quality) → computes strategic distinction verdict |
| `trade/package_builder.py` | Trade | Builds `PackageBuilderResult` with two offers: `Aggressive Open` (optionally trims one send asset if counterparty profile shows value_loss pattern) and `Fair Close` (sends as-is); uses pitch angles for aggressive reasoning |
| `trade/reroute_engine.py` | Trade | Generates up to `MAX_REROUTES` (3) suggestions: up to 2 better target alternatives at same position ranked by direction+market lens, plus 1 cheaper send alternative if available |
| `snapshots/models.py` | Snapshots | Pydantic models: `SnapshotStatus`, `SnapshotTriggerResponse` |
| `snapshots/snapshot_service.py` | Snapshots | Captures full league state (rosters, standings, directions, scorecards, player values, traded picks) as JSON in `league_snapshots`; auto-selects `full` vs `delta` type (one full per calendar month, deltas thereafter); delta tracks `changed_players` and `changed_rosters` |
| `routers/health.py` | Router | `GET /health/{league_id}` — ingest run status + gap list |
| `routers/ingest.py` | Router | `POST /ingest/{league_id}?run_type=full\|incremental`, `GET /ingest/status/{league_id}` |
| `routers/corrections.py` | Router | `POST /corrections/`, `GET /corrections/{league_id}`, `DELETE /corrections/{correction_id}` |
| `routers/intelligence.py` | Router | `POST /intelligence/compute/{league_id}`, `GET /intelligence/scorecard/{league_id}/{roster_id}`, `GET /intelligence/direction/...`, `GET /intelligence/player-value/...` |
| `routers/dashboard.py` | Router | `GET /dashboard/summary` (all leagues), `GET /dashboard/league/{league_id}` (league detail with risers/fallers and exploit windows); both derived from snapshot state comparison |
| `routers/snapshots.py` | Router | `POST /snapshots/trigger`, `GET /snapshots/status` |
| `routers/profiling.py` | Router | `GET /profiling/leagues/{league_id}/managers`, `GET /profiling/leagues/{league_id}/managers/{roster_id}`, `POST /profiling/leagues/{league_id}/managers/compute` |
| `routers/trade.py` | Router | `POST /trade/evaluate`, `GET /trade/players/search`, `GET /trade/picks/search` |
| `routers/deps.py` | DI | FastAPI dependency providers for read and write DuckDB connections |

### Backend — Alembic Migrations (`backend/alembic/versions/`)

| File | What It Adds |
|------|-------------|
| `001_initial_schema.py` | Core tables: leagues, rosters, standings, traded_picks, transactions, players, ingest_runs |
| `002_add_player_stats_weekly.py` | `player_stats_weekly` table |
| `003_add_adp_baseline.py` | `player_adp_baseline` table |
| `004_phase2_output_tables.py` | `team_scorecards`, `team_directions`, `player_values` |
| `005_league_snapshots.py` | `league_snapshots` table |
| `006_phase4_profiling_tables.py` | `manager_profiles`, `manager_pitch_angles` |

### Backend — Tests (`backend/tests/`)

| File | What It Covers |
|------|---------------|
| `conftest.py` | Full in-memory DuckDB schema; fixtures: `db`, `phase2_seed_data`, `phase3_seed_data`, `profiling_seed_data`, `trade_seed_data`; extensive realistic seed data |
| `test_gap_detector.py` | `GapDetector.detect_unmapped_scoring_keys`, `detect_missing_season_stats` |
| `test_ingest_service.py` | Full ingest via `FakeSleeperClient`; full/incremental run types; duplicate run blocking; cursor advancement |
| `test_sleeper_mapper.py` | `SleeperMapper` field mapping for all entity types |
| `test_league_repo.py` | Upsert idempotency for leagues, rosters, standings, transactions |
| `test_corrections.py` | Correction survival through reingest; duplicate upsert semantics |
| `test_scorecard_engine.py` | All subscores present; range [0,1]; corrections affect scoring; missing stats defaults; fragility availability proxy |
| `test_valuation_engine.py` | All 12 components + 5 lenses present; PPR/superflex adjustments; direction reweight |
| `test_direction_engine.py` | Valid label output; contender/rebuild signals; confidence range; alternates; delta structure; move matrix completeness |
| `test_intelligence_service.py` | Idempotent compute; scorecard changes trigger direction recompute |
| `test_intelligence_router.py` | HTTP-level: compute and retrieve scorecard/direction |
| `test_profiling_engine.py` | Trade side parsing; value delta sign; fallback ADP; pick values; exploitation classification (primary/secondary/threshold/incoherence/missing direction); exploitability score range; pitch angle count; evidence string format |
| `test_profiling_router.py` | `POST compute`, `GET managers`, `GET manager/{roster_id}` — HTTP-level roundtrip |
| `test_dashboard_router.py` | Snapshot trigger + status; dashboard summary with exploit window; league detail with risers/fallers |
| `intelligence/test_trade_engine.py` | Evaluate trade; 7 dimensions present and in range; strategic distinction verdicts (advancing/negative/neutral); manager profile absence returns LOW confidence |
| `intelligence/test_package_builder.py` | Package build labels; personalized reasoning when profile exists |
| `intelligence/test_reroute_engine.py` | Reroute generation (better target, better package) |
| `integration/test_trade_router.py` | `POST /trade/evaluate`, with/without reroutes+package; player search; pick search |

### Frontend — Source (`frontend/src/`)

| File | What It Does |
|------|-------------|
| `main.tsx` | React 18 root; wraps in `QueryClientProvider` and `RouterProvider` |
| `api/types.ts` | TypeScript types: `DashboardLeagueSummary`, `LeagueDetailResponse`, `ManagerProfile`, `ManagerSummary`, `SnapshotStatus`, `TradeAsset`, `TradeEvaluation`, `DimensionScore`, `StrategicDistinction`, `RerouteResult`, `PackageBuilderResult`, `PlayerSearchResult`, `PickSearchResult`, `ThirdPartyTrade` |
| `api/queries.ts` | TanStack Query options: `dashboardSummaryOptions`, `leagueDetailOptions`, `snapshotStatusOptions`, `managerSummariesOptions`, `managerProfileOptions` |
| `lib/utils.ts` | `cn()` classname merge utility |
| `routes/__root.tsx` | Root layout with nav sidebar; links to dashboard, trade evaluator |
| `routes/index.tsx` | Dashboard home: league card list, ingest status |
| `routes/league.$leagueId.tsx` | League detail: direction label, confidence badge, weakness, snapshot status, risers/fallers, exploit windows, link to managers and trade evaluator |
| `routes/league.$leagueId.managers.tsx` | Manager list: `ManagerListRow` per roster with exploitability score and top pitch angle |
| `routes/league.$leagueId.managers.$managerId.tsx` | Manager dossier: three-tab view (Overview, Trade History, Pitch Angles) |
| `routes/trades.tsx` | Trade evaluator: league ID + roster IDs, asset bucket builder (send/receive), multi-team third-party legs, player/pick search, evaluation mutation, output panels |
| `components/LeagueCard.tsx` | League summary card used on dashboard |
| `components/SnapshotStatus.tsx` | Shows time since last snapshot |
| `components/RisersFallersList.tsx` | Risers/fallers player delta list |
| `components/ExploitWindowPanel.tsx` | Exploit window manager cards with triggers |
| `components/ManagerListRow.tsx` | Single manager row in manager list |
| `components/DossierOverviewTab.tsx` | Overview tab: exploitation classification, roster summary, aggregate trade stats |
| `components/DossierPitchAnglesTab.tsx` | Pitch angles tab: ranked deal archetypes with send/avoid guidance |
| `components/DossierTradeHistoryTab.tsx` | Trade history tab: chronological trade log with value deltas |
| `components/trade/AssetChip.tsx` | Removable chip for a player or pick in bucket panels |
| `components/trade/DimensionScoreRow.tsx` | Single dimension score row with score bar, confidence badge, reasoning |
| `components/trade/EvaluationOutputPanel.tsx` | Full 7-dimension trade result; strategic distinction banner; reroutes/package buttons |
| `components/trade/PackageBuilderPanel.tsx` | Package builder result: aggressive open + fair close offers |
| `components/trade/RerouteSheet.tsx` | Slide-out sheet listing reroute suggestions |
| `components/trade/StrategicDistinctionBanner.tsx` | Colored verdict banner (advancing/negative/neutral) |
| `components/ui/` | Shadcn/ui primitives: badge, button, card, separator, skeleton |
| `routeTree.gen.ts` | TanStack Router generated route tree (do not edit manually) |
| `vite.config.ts` | Vite config with `/api` proxy to `localhost:8000` |

---

## Data Flow

**Full Ingest → Intelligence → Profiling → Trade Evaluate**

1. `POST /ingest/{league_id}` → `IngestService.run()` fetches from Sleeper API, maps, upserts into DuckDB, applies corrections, detects gaps, takes snapshot.
2. `POST /intelligence/compute/{league_id}` → `IntelligenceService.compute_league()` → `ScorecardEngine` → `DirectionEngine` → `ValuationEngine`; persists to `team_scorecards`, `team_directions`, `player_values`.
3. `POST /profiling/leagues/{league_id}/managers/compute` → `ProfilingEngine.compute_all_profiles()` reads trade history, classifies exploitation, scores exploitability, selects pitch angles; persists to `manager_profiles`, `manager_pitch_angles`.
4. `POST /trade/evaluate` → `TradeEngine.evaluate()` resolves asset values from `player_values`, loads direction from `team_directions`, loads manager profile from `manager_profiles`; computes 7 dimension scores; optionally invokes `RerouteEngine` and `PackageBuilder`.

**Dashboard reads** derive from `league_snapshots` — they compare the two most recent snapshot payloads to surface risers/fallers and scan raw transaction data for exploit window triggers.

---

## Database Schema (Tables in Use)

**Core ingestion:** `leagues`, `rosters`, `standings`, `traded_picks`, `transactions`, `players`, `ingest_runs`, `corrections`

**Stats baseline:** `player_stats_weekly`, `player_adp_baseline`

**Intelligence output:** `team_scorecards`, `team_directions`, `player_values`

**Snapshots:** `league_snapshots`

**Profiling output:** `manager_profiles`, `manager_pitch_angles`

All tables are DuckDB, accessed via raw SQL (no ORM at runtime). SQLAlchemy `Table` definitions in `db/models.py` exist for reference but are not used at query time.

---

## Test Coverage Assessment

### Genuinely Covered

- **Ingestion** — `FakeSleeperClient` drives full service integration; full and incremental modes tested; duplicate run guard tested; cursor advancement confirmed.
- **Sleeper mapping** — all entity types mapped and validated.
- **Scorecard engine** — all 9 dimensions present and in [0,1]; corrections applied before scoring; pick capital dual-source; missing stats defaults; fragility proxy.
- **Valuation engine** — all 12 components + 5 lenses; PPR, superflex, TEP adjustments; direction reweighting; missing stats fallback.
- **Direction engine** — label assignment, confidence range, alternates, delta, move matrix completeness, ranked moves.
- **Intelligence service** — idempotent compute confirmed.
- **Profiling engine** — trade side parsing, value delta sign, pick values, primary/secondary exploitation classification, threshold logic, timing error detection, directional incoherence, missing direction fallback, pitch angle count, evidence string format.
- **Profiling router** — compute, list, get endpoints HTTP-tested.
- **Trade engine** — all 7 dimensions present and in [0,100]; strategic distinction advancing/negative/neutral; manager profile absence degrades to LOW.
- **Package builder** — labels and personalization.
- **Reroute engine** — better target and cheaper package generation.
- **Trade router** — evaluate with and without reroutes/package; player search; pick search.
- **Dashboard router** — snapshot trigger/status; summary and league detail endpoints.
- **Corrections** — survive reingest; duplicate upsert semantics.

### Gaps and Missing Coverage

- **`apply_corrections()`** — the method only logs corrections, does not actually mutate any table. No test verifies that correction data actually flows back to the underlying `players` or `rosters` tables (it doesn't — corrections are applied only in `ScorecardEngine._apply_corrections()` at compute time, but there is no test asserting the full end-to-end path: create correction → ingest → compute → scorecard reflects correction).
- **`OverrideService.apply_corrections()`** — function is a stub that logs and returns a count but takes no action on data. This is architecturally misleading because `IngestService.run()` calls it, but corrections only affect intelligence output through the scorecard engine's in-memory application.
- **`NflDataPyLoader`** — `load_weekly_stats()` and `upsert_weekly_stats()` are not tested (no test invokes the real `nfl_data_py` library or mocks it).
- **`load_adp_baseline()`** — not directly tested; startup calls it but there is no test asserting correct CSV parsing and upsert behavior.
- **`compute_fantasy_points()`** — not tested.
- **`SleeperClient`** — the real async client is never exercised; only `FakeSleeperClient` is used. No test covers retry behavior (429 → backoff → success).
- **Snapshot delta computation** — `_compute_delta()` in `SnapshotService` is indirectly tested through the dashboard router test, but no dedicated unit test exercises the diff logic directly.
- **`profiling_router.get_manager_profile()`** — the endpoint recomputes on every call (does not use the cached `ProfilingRepo.get_profile()`). No test exercises the path where `evidence_count == 0` triggers a 404.
- **Frontend** — zero frontend tests exist (no Vitest setup, no component tests, no E2E).
- **Multi-team trade legs** — `third_party_trades` is parsed and passed through the request model but `TradeEngine.evaluate()` does not use it. No test documents this limitation.
- **Dashboard risers/fallers** — requires two snapshots with different player values; the test in `test_dashboard_router.py` partially exercises this path but only from the router level; no unit test for `_build_risers_fallers()` in isolation.

---

## Quality Gaps and Incomplete Implementations

### Critical: `apply_corrections()` is a No-Op

`backend/src/fantasy/corrections/override_service.py` line 141 — `apply_corrections()` reads corrections from the DB, logs each one, and returns the count. It does not write back to `players`, `rosters`, or any other table. `IngestService.run()` calls it after every ingest, but corrections only propagate to intelligence output through `ScorecardEngine._apply_corrections()`, which reads the `corrections` table at compute time and applies them in-memory. Any caller expecting `apply_corrections()` to mutate the source tables will be surprised.

### Partial: Multi-Team Trades Not Scored

`backend/src/fantasy/trade/trade_engine.py` — `TradeRequest.third_party_trades` is accepted and passed through the API but `TradeEngine.evaluate()` does not consume it. The third-party legs are invisible to all 7 dimension scores. The frontend UI shows a note that "scoring remains user-centric today," which documents the known gap.

### Stub: Manager Name from `owner_id`

`backend/src/fantasy/profiling/profiling_engine.py` line 511 — `manager_name` is set to `roster_row[0]` which is `owner_id` (the Sleeper user ID string), not a display name. The Sleeper API does provide display names via `/league/{league_id}/users` but this endpoint is not called during ingest. The dossier page falls back gracefully (`Roster {roster_id}`) but the owner IDs are shown in the UI in places.

### Weak: ADP Baseline Matching

`backend/src/fantasy/ingestion/nfl_data_loader.py` `load_adp_baseline()` — the function accepts a CSV with a `player_id` column, but ADP CSVs from FantasyPros do not include Sleeper player IDs. The CSV import silently stores `None` for `player_id` if the column is absent, and downstream joins on `player_id` will find nothing. There is no name-based fuzzy matching fallback. This means ADP data only works if the CSV is pre-processed to include Sleeper player IDs.

### Minor: `_score_positional_insulation()` Logic

`backend/src/fantasy/intelligence/scorecard_engine.py` line 418 — the insulation score checks whether a starter's position appears anywhere in the bench position list, but does so by checking `starter_position in bench_positions` (a list, not a set), which is O(n) and also only looks at the first `len(required_slots)` starters. The logic does not correctly account for duplicate positions in the bench (e.g., 3 WR bench players providing insulation at 2 WR slots). The score can undercount insulation.

### Minor: Pick Capital Double-Counts

`backend/src/fantasy/intelligence/scorecard_engine.py` `_score_pick_capital()` — constructs `untouched` as all picks in the next 3 seasons not found in `traded_away_set`, then combines them with `traded` (received picks). This means a roster that traded away its own pick and received it back will count the traded pick twice (once in `traded` because they received it, and once in `untouched` if the `traded_away_set` check passes). The logic uses `traded_away_set` based on `roster_id == inputs.roster_id` which refers to the original pick owner, not the receiver, so this is a genuine potential double-count in certain pick trade scenarios.

### Minor: Dashboard Exploit Window — No Profiling Integration

`backend/src/fantasy/routers/dashboard.py` `_build_exploit_windows()` — the trigger logic is derived entirely from raw transaction patterns (trade count, pick movement, position chase). It does not load or use the pre-computed `manager_profiles` / `manager_pitch_angles` data from the profiling phase. The profiling engine computes exploitation classifications that are richer, but the dashboard triggers bypass them entirely.

### Minor: CORS Configured as Open

`backend/src/fantasy/main.py` line 47 — `allow_origins=["*"]` — fully open CORS. Appropriate for local development but must be locked down for any network-accessible deployment.

### Missing: Input Validation on Roster IDs

`backend/src/fantasy/routers/trade.py` — roster IDs are passed as raw integers and trusted directly. There is no check that `user_roster_id` or `counterparty_roster_id` actually belong to `league_id`. A mismatched roster/league pair silently returns degraded results (e.g., direction returns `None`, manager profile returns `None`).

### Missing: Week Hardcoding for Trade History Pick Dates

`backend/src/fantasy/profiling/profiling_engine.py` line 448 — in `_build_trade_history()`, pick labels are hardcoded as `"2026 Round {round_number} pick"` regardless of the actual pick season from the transaction payload. Only received/sent player names and pick rounds are read from the transaction; the pick year is not passed through to the history display.

---

## Frontend Completeness

All UI surfaces listed in the route tree are implemented with real data (not stubs):

- Dashboard index with league cards — fully implemented.
- League detail with risers/fallers and exploit windows — fully implemented.
- Manager list and dossier (overview, trade history, pitch angles) — fully implemented.
- Trade evaluator with multi-team support, player/pick search, 7-dimension output, reroutes sheet, package builder — fully implemented.

The frontend has no test suite. All components use TanStack Query for data fetching with `staleTime` caching. Routing uses TanStack Router with file-based route generation. The Vite dev proxy routes `/api/*` to `http://localhost:8000`.

---

## Implementation Status Summary

| Feature | Backend | Frontend | Tests |
|---------|---------|----------|-------|
| Sleeper ingestion (full + incremental) | Complete | N/A | Good |
| Weekly stats loading (nfl_data_py) | Complete | N/A | None |
| ADP baseline loading | Complete (CSV only) | N/A | None |
| Corrections CRUD | Complete | Not surfaced in UI | Good |
| Team scorecard (9 dimensions) | Complete | N/A | Good |
| Direction classification (8 labels) | Complete | N/A | Good |
| Player valuation (12 comp + 5 lenses) | Complete | N/A | Good |
| Intelligence persistence + lazy compute | Complete | N/A | Partial |
| Manager profiling + exploitation | Complete | Complete | Good |
| Pitch angles | Complete | Complete | Partial |
| Trade evaluation (7 dimensions) | Complete | Complete | Good |
| Trade reroutes | Complete | Complete | Good |
| Package builder | Complete (shallow) | Complete | Partial |
| Multi-team trade scoring | Not implemented | UI only | None |
| Snapshots (full + delta) | Complete | N/A | Partial |
| Dashboard (summary + league detail) | Complete | Complete | Partial |
| Risers/fallers | Complete | Complete | Partial |
| Exploit windows | Complete | Complete | Partial |
| Manager dossier frontend | N/A | Complete | None |
| Frontend test suite | N/A | Not started | None |
