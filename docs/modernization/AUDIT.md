# Fantasy v2 Modernization Audit

Status: baseline discovery audit; implementation continued after this snapshot.

Audit date: 2026-08-01

Audit worktree: `/Users/jakyeamos/projects/Fantasy/.worktrees/gpt56-v2`

Audit branch: `codex/rebuild-gpt56`

Audit baseline commit: `ec614a53a7614f6375277082881cb4899eeb695b`

## Scope and evidence rules

This audit follows the requested 5.6-led v2 workflow. At the audit date it
established a protected clean-HEAD baseline, documented the product and
architecture, and recorded a target direction without changing application
code. The later implementation and verification work is recorded in
`PROGRESS.md` and the evidence files in this directory; statements about the
audit date are intentionally historical.

The primary `dev` checkout was already dirty before this work. Its existing
changes were preserved and were not included in the clean baseline run:

- modified planning state/configuration;
- modified Sleeper ingestion source and tests;
- modified dense player metadata CSV; and
- a staged deletion of `.tracker/PROJECT_TRUTH.md`.

An untracked `data/fantasy.duckdb.wal` was visible in the initial status
snapshot and was absent from the final status check. No application process
was pointed at the primary database as an application write target, and the
audit did not intentionally delete or restore that artifact; its preservation
is therefore unresolved and remains a human follow-up item.

The v2 worktree was created from `HEAD` so the audit can distinguish committed
product behavior from that in-progress overlay. A local symlink for the
relative `eslint-plugin-anti-slop` development dependency and generated
dependency/build artifacts live only in the disposable worktree environment.

Evidence labels in this document mean:

- **Observed**: directly reproduced from files, commands, the copied database,
  or the running local app.
- **Inferred**: a design or causal interpretation based on observed evidence.
- **Blocked**: a required check could not run under the available boundary.
- **Unknown**: the repository does not currently provide enough evidence.

## Executive finding

Fantasy already contains substantial domain value: a local dynasty football
intelligence engine with Sleeper ingestion, league-specific scoring, roster and
lineup analysis, manager dossiers, trade and pick intelligence, rookie/prospect
models, waivers, weekly context, portfolio exposure, freshness warnings, and a
recommendation-oriented dashboard.

The main v2 problem is not missing functionality. It is that the product has
grown as a sequence of phases and feature surfaces rather than as one coherent
decision workflow. The backend, schema, API, frontend route tree, and planning
artifacts all show that history. The result is a valuable but wide product with
high coupling, multiple schema authorities, uneven verification depth, and a UI
that can expose the same decision through several competing destinations.

The recommended rebuild should preserve the domain engines and historical data
while replacing the application shell and integration seams around them. The
target should be a recommendation-first front office: one daily decision queue,
one league workspace, one canonical recommendation contract, and explicit
source/freshness/confidence evidence on every decision.

## Baseline execution

The clean v2 worktree was installed and tested from the documented commands.

| Check | Result | Evidence |
| --- | --- | --- |
| Backend dependency install | **Pass**; `uv sync --project .worktrees/gpt56-v2/backend` installed the locked environment after a network-permission retry | `backend/pyproject.toml`, `backend/uv.lock` |
| Frontend dependency install | **Pass**; `pnpm --dir .worktrees/gpt56-v2/frontend install --frozen-lockfile` | `frontend/package.json`, `frontend/pnpm-lock.yaml` |
| Backend tests | **2 failures, 550 passed** in 149.64s | `backend/tests/test_command_center_acceptance.py::test_command_center_manager_action_prefills_trade_offer`; `backend/tests/trends/test_opportunity_engine.py::test_buy_target_solving_lineup_gap_outranks_larger_raw_gap` |
| Frontend lint | **Pass**; `pnpm lint` | `frontend/package.json` maps lint to `tsc --noEmit` |
| Frontend typecheck | **Pass**; `pnpm typecheck` | `frontend/package.json` |
| Frontend build | **Pass**; Vite transformed 298 modules and built in 982ms | `frontend/package.json`, `frontend/vite.config.ts` |
| Frontend dead-code check | **Pass**; `pnpm audit:dead-code` | `frontend/package.json` |
| Frontend format check | **Blocked/fail**; `prettier: command not found` | `frontend/package.json` declares the script but not the `prettier` dependency |
| Frontend render smoke | **Process exit 0 but warning**; Vite logged `listen EPERM ... 0.0.0.0:24678` while the test completed | `frontend/tests/marketGapRender.test.mjs` starts Vite internally |
| FastAPI startup | **Pass** against copied DuckDB; application startup completed | `backend/src/fantasy/main.py`, `backend/src/fantasy/startup_tasks.py` |
| API contract | **Pass** for runtime generation; OpenAPI exposed 65 paths | `backend/src/fantasy/main.py`, `backend/src/fantasy/routers/*.py` |
| Dashboard API | **Pass**; `/dashboard/summary` returned two seeded leagues | `backend/src/fantasy/routers/dashboard.py` |
| Browser route check | **Pass after explicit readiness waits** for dashboard, opportunities, portfolio, trades, draft room, league briefing, waivers, managers, and rookie board; no relevant console errors or horizontal overflow observed | `frontend/scripts/browserSmoke.mjs`, captured evidence below |
| Repository browser smoke | **Harness defect**; `networkidle` waits against Vite's persistent HMR connection and did not complete in a bounded time | `frontend/scripts/browserSmoke.mjs` uses `waitUntil: "networkidle"` |

The two backend failures are not attributed to the v2 worktree changes; they
are present on the clean baseline and require disposition before a later
implementation milestone can claim a green suite. The first failure means the
manager action builder did not emit the expected prefilled trade offer. The
second means a larger raw market gap outranked a smaller gap that solved an
active lineup need, contrary to the test's stated product rule.

### Runtime data snapshot

The app was exercised using a copied database at
`/private/tmp/fantasy-gpt56-baseline.duckdb`; the user's local database was not
used as an application write target. The copied database contained:

- 43 tables;
- 2 leagues and 24 rosters;
- 369 players and 404 transactions;
- 762 player-value rows, 24 team scorecards, 24 team directions, and 24 waiver
  recommendation rows;
- 294 ingest runs and 1,091 league snapshots; and
- 771 historical prospect feature rows.

The live dashboard returned `AMG` and `The Loft`. The API returned 200 for the
principal dashboard and feature requests exercised by the browser. `/health`
and `/health/` returned 404 because the health contract is
`/health/{league_id}`, not a process-level health endpoint. That is an
operability gap rather than a runtime crash.

### Screenshots

Representative baseline captures are stored with this audit:

- `docs/modernization/evidence/baseline-dashboard.png`
- `docs/modernization/evidence/baseline-opportunities.png`

The dashboard capture shows a visually coherent, restrained light theme with a
strong "Top moves today" queue, freshness lane, league cards, and portfolio
entry point. It is also a long page with several levels of summary and repeated
navigation chrome. The opportunity capture was taken during the route's loading
state and shows a large skeleton surface; the route works, but readiness is
not explicit enough for a reliable screenshot or smoke harness.

## Current product and user journeys

The product definition in `.planning/PROJECT.md` is a personal dynasty football
front-office system for one to three Sleeper leagues. Its intended value is not
rankings; it is context-aware advice about what a team is, what direction it
should take, who to trade with, what package to make, and whether a player or
pick decision is sharp in that league.

The committed product currently supports these journeys:

1. **Open the command center.** Load cross-league summaries, stale-data lanes,
   and a ranked Top Moves queue.
2. **Enter a league briefing.** Read direction, scorecards, lineup strength,
   weekly edge, competitive context, snapshots, and roster-level actions.
3. **Act on a trade opportunity.** Open Trade Lab with a player/package
   prefill, inspect market fairness, roster fit, direction fit, manager pitch,
   reroutes, and multi-team sidecar evaluations.
4. **Exploit a manager.** Read the manager list and dossier, including trade
   history, pitch angles, rookie/pick tendencies, urgency, and target/send
   recommendations.
5. **Manage weekly and waiver decisions.** Inspect start/sit edge, lineup gaps,
   injury/usage/matchup freshness, waiver recommendations, FAAB ranges, roster
   hygiene, and orphan intake.
6. **Make draft and rookie decisions.** Use picks, draft-order rules, rookie
   boards, draft room guidance, startup mode, draft grades, and prospect
   evidence.
7. **Review portfolio risk.** Inspect cross-league player exposure, correlated
   risk, hedge/watch recommendations, and retrospective snapshots.
8. **Refresh local truth.** Re-run Sleeper ingestion and downstream caches,
   refresh market/team context, inspect gaps, and acknowledge unsupported league
   formats.

The product's intended user is technically capable and accepts local setup, but
the decision surface should still be understandable without knowing the
internal phase history or the difference between a cache, snapshot, freshness
domain, and source table.

## Architecture and request/data flow

### Observed structure

- FastAPI backend in `backend/src/fantasy` with 26 top-level domain packages and
  26 router files.
- React 19/Vite/TypeScript frontend with 19 file-based routes, TanStack Router,
  and React Query.
- DuckDB persistence at `data/fantasy.duckdb`, with 25 Alembic version files.
- External adapters for Sleeper, FantasyCalc, nflreadpy/nfl-data-py, and local
  curated CSVs.
- API response shapes duplicated manually in the 1,235-line
  `frontend/src/api/types.ts` file and query definitions in the 500-line
  `frontend/src/api/queries.ts` file.

The dominant flow is:

`browser route -> React Query hook -> FastAPI router -> engine/repository -> DuckDB`

Refresh routes additionally run:

`router -> ingest adapter -> mapper -> base tables -> derived engines -> caches/snapshots/freshness`

The global React root also fetches `dashboardSummaryOptions` for navigation,
route metadata, and snapshot chrome. That makes the dashboard summary a shell
dependency for every route, even when the user is in Trade Lab, a manager
dossier, or a draft surface (`frontend/src/routes/__root.tsx`).

### Valuable parts worth retaining

- The product mission and local-first scope are unusually clear in
  `.planning/PROJECT.md`.
- Sleeper is a practical first integration and its adapter isolates the public
  API details in `backend/src/fantasy/ingestion/sleeper_client.py` and
  `sleeper_mapper.py`.
- League-specific settings, superflex/TEP/PPR handling, roster constraints,
  draft-order rules, corrections, and unsupported-format acknowledgments are
  meaningful domain concepts, not generic dashboard fields.
- The recommendation engines expose actionable lanes rather than stopping at
  data display: trade, manager, waiver, weekly, rookie, pick, and portfolio.
- The Edge Radar decision to feed market discoveries into the command center
  instead of creating another top-level destination is a good product
  instinct and should be preserved.
- Freshness, gaps, confidence, direction alternates, and market-vs-model
  evidence are the right ingredients for a trustworthy decision product.
- The current UI already has a useful visual language: strong typography,
  restrained surfaces, visible urgency/confidence tags, and compact action
  cards. The v2 should refine this rather than discard the strongest signals.
- The test suite is large enough to encode substantial domain behavior: 88
  backend test files and 544 test declarations were present at audit time.

## Accidental complexity and architectural weaknesses

### 1. Schema authority is split

There are three schema writers: Alembic migrations in
`backend/alembic/versions`, runtime compatibility DDL in
`backend/src/fantasy/startup_tasks.py`, and test bootstrap DDL in
`backend/test_support/schema_sql*.py` and `backend/tests/conftest.py`.
`.tracker/PROJECT_TRUTH.md` and `.planning/STATE.md` already identify this as a
fragile triple-write arrangement.

Immediate cause: every new table or column may require synchronized edits in
multiple places. Systemic failure mode: a migration can pass while a direct
`uvicorn` startup, a test fixture, or a copied database sees a different schema.
Durable prevention: one migration authority, a disposable migrated test
database, and an explicit schema compatibility test. Verification: migration
upgrade from an empty database, upgrade from a realistic legacy copy, and
read/write contract tests at each cutover.

### 2. Domain engines and routers are oversized

The largest committed files include `routers/dashboard.py` at 1,929 lines,
`lineup/hygiene_engine.py` at 1,013, `lineup/lineup_engine.py` at 991,
`profiling/profiling_engine.py` at 915, and `actions/command_center.py` at 811.
The largest frontend files include `api/types.ts` at 1,235 lines,
`routes/trades.tsx` at 592, `routes/league.$leagueId.tsx` at 519, and
`routes/__root.tsx` at 494.

Immediate cause: features were added as phase slices and then split only when a
local size gate was hit. Systemic failure mode: changes cross routing,
computation, persistence, and presentation concerns, making a small product
rule difficult to verify end to end. Durable prevention: bounded use-case
modules, read-model projections, and feature-owned contracts with explicit
dependency direction. Verification: module-level tests plus architecture
checks for import direction and route/use-case ownership.

### 3. The application has many surfaces but no canonical decision object

The same underlying evidence appears as command-center actions, opportunity
cards, recommendation cards, trade suggestions, weekly edge cards, waiver
recommendations, and roster hygiene rows. Some already share market-gap and
freshness concepts, but the API and frontend contracts remain feature-shaped.

Immediate cause: each phase added its own model and response shape. Systemic
failure mode: urgency, confidence, timing, freshness, acceptable price, risk,
and next-click behavior can drift between surfaces. Durable prevention: a
canonical `DecisionCard`/`Action` contract with explicit evidence provenance and
capability states. Verification: contract fixtures asserting the same decision
renders equivalently in the dashboard, league page, and destination workflow.

### 4. Startup behavior mixes migration, compatibility, and refresh concerns

`dev.sh` runs Alembic before Uvicorn, while `fantasy.main` runs
`ensure_runtime_schema`, ADP loading, and optionally a background refresh during
application lifespan. Direct Uvicorn usage does not run Alembic first, as the
project state itself warns.

Immediate cause: the local launcher is doing migration and the application is
also attempting to be tolerant of schema drift. Systemic failure mode: a
developer or test can start the app with an apparently healthy but incomplete
database. Durable prevention: a single explicit `db migrate`/`db verify` gate,
startup that refuses incompatible schemas, and refresh as a separately invoked
operation. Verification: clean-start, stale-schema, partially-migrated, and
refresh-failure scenarios.

### 5. The frontend shell is coupled to data and feature history

`frontend/src/routes/__root.tsx` owns theme state, mobile navigation, route
metadata, dashboard summary fetching, snapshot-age display, primary navigation,
and global shell layout. This makes the root a high-blast-radius change surface.

Immediate cause: the shell accumulated cross-cutting behavior as routes were
added. Systemic failure mode: a dashboard API or navigation change can affect
every screen and every browser smoke route. Durable prevention: a thin app shell,
explicit workspace context, route-local queries, and a tested navigation model.
Verification: shell tests with the backend unavailable, route-level data tests,
and browser checks for loading/empty/error states.

## Product and UX findings

### Strengths observed

- The dashboard prioritizes a ranked action queue and uses plain-language
  rationales such as “Buy low: Matthew Stafford”.
- Stale domains are visible and actionable rather than silently hidden.
- The screenshot shows a consistent border/surface/typography system and no
  horizontal overflow at 1440px.
- The route sweep loaded the principal routes without relevant browser console
  errors after explicit data readiness.

### Weaknesses observed or inferred

- The current navigation makes Dashboard, Managers, Portfolio, Trade Lab, and
  Rookie Board look like peers even though some are destinations, some are
  workflows, and some are league-scoped tools.
- The dashboard is long and repeats system status, snapshot age, league
  summaries, and portfolio entry points. The visual hierarchy is coherent but
  not yet optimized for “what should I do next?” at one glance.
- Opportunity Feed can expose a large skeleton state while the route is already
  structurally rendered. The baseline screenshot captured that state, and the
  browser harness has no explicit data-ready contract.
- The UI uses a terminal/cockpit metaphor heavily. It is distinctive, but labels
  such as `TERMINAL`, `PROVEN`, `SYSTEM STATUS`, and `LIVE MARKET` compete with
  the actual football decision in dense views.
- Loading, empty, stale, blocked-by-format, degraded-source, and manual-review
  states are not represented by one shared design system. They are implemented
  feature by feature.
- The app is desktop-first in its captured composition. Mobile behavior is
  partially covered by CSS and a hidden mobile devtools rule, but a complete
  narrow-width journey was not established by the baseline harness.

## Security, privacy, and data-integrity findings

### Observed

- The product is intentionally local-only and has no authentication system,
  documented in `.planning/PROJECT.md`.
- FastAPI configures `allow_origins=["*"]` together with
  `allow_credentials=True` in `backend/src/fantasy/main.py`.
- Mutating ingestion, recompute, correction, snapshot, and acknowledgment routes
  are present in the same unauthenticated local API as read routes.
- Sleeper and FantasyCalc network clients use retries and timeouts, but
  external-source provenance and partial-result behavior are not represented by
  one cross-source contract.
- A secrets scan is not configured in the Pronto quality projection. The latest
  quality snapshot is stale and reports 121 unreviewed findings, including 60
  high-severity findings, with no repository-owned disposition contract.
- DuckDB is a local file and snapshot/ingest history is persistent. The project
  does not currently document a formal backup/restore or migration rollback
  procedure.

### Risk and prevention

The current local-only scope reduces exposure but does not make wildcard CORS,
unbounded mutation routes, or unverified migration behavior safe if the process
is accidentally bound beyond localhost. v2 should bind to loopback by default,
restrict CORS to the known frontend origin, distinguish read and mutation
capabilities, require explicit confirmations for destructive or broad refresh
operations, and add a secrets scan plus local backup/restore verification.

Persistent data must be treated as valuable even without external users. Every
schema cutover needs a copied database, row-count/key reconciliation, checksum
or export manifest, and a tested rollback path.

## Testing, performance, observability, and developer experience

### Testing

The backend suite has broad domain coverage, but the clean baseline has two
failures and the frontend has only five test files with five declaration sites
reported by the inventory scan. The browser smoke script checks route text and
horizontal overflow, but its `networkidle` strategy is incompatible with the
development server's persistent HMR connection and its dashboard check relies
on a fixed retry/data-load pattern.

The test suite also has a large acceptance fixture surface. That is useful for
behavior, but it increases the cost of changing the canonical recommendation
contract unless fixtures are organized around stable decision scenarios.

### Performance

- The global root fetches dashboard summary data on every route.
- `dashboard.py` and `command_center.py` are large orchestration surfaces.
- Similar-player and opportunity enrichment has already required bounded
  behavior and degraded states, according to `.planning/PROJECT.md` and
  `.planning/STATE.md`.
- The database contains many derived tables and 1,091 snapshots, but there is
  no documented retention/compaction policy.
- The frontend build is fast on the current machine, but the route bundle still
  contains a 273.85 kB gzip-uncompressed-ish main JS asset before browser cache
  and a 66.48 kB utility chunk; no performance budget is enforced.

### Observability

Ingest runs and freshness domains are valuable foundations. Logs include ingest
run identifiers and degraded notes in current code, but the API does not expose
a single process health/readiness contract, and failures are not consistently
correlated across ingestion, derived recompute, and the browser request. The
current runtime probe returning 404 for `/health` is concrete evidence that the
operational contract is underspecified.

### Developer experience

The root README provides useful setup commands, but:

- `frontend/package.json` has a `format` script without a declared Prettier
  dependency;
- the frontend depends on a machine-relative local package path;
- there is no `.github` workflow visible in the repository file inventory;
- migration, runtime compatibility DDL, and test schema setup are duplicated;
- current planning documents report phases and counts that have drifted from the
  roadmap's original twenty-phase framing; and
- direct app startup and the documented launcher have different schema
  guarantees.

## External contracts and migration constraints

### Contracts to preserve or explicitly replace

1. **Sleeper public API**: league metadata, rosters, users, traded picks,
   transactions by week, NFL state, drafts, draft picks, player catalog, and
   weekly stats are consumed by `SleeperClient`.
2. **FantasyCalc values API**: dynasty values, market ranks, and trend movement
   feed market baselines and model-vs-market gaps.
3. **nflreadpy/nfl-data-py and curated data files**: historical stats, prospect
   features, draft capital, team context, and dense player metadata feed models.
4. **DuckDB file contract**: local data lives at `FANTASY_DB_PATH`, defaulting to
   `data/fantasy.duckdb`; users can have valuable corrections, snapshots, and
   derived outputs in the file.
5. **Frontend deep links**: routes encode league, roster, manager, player,
   pick, filter, and trade-prefill context. Existing links must either resolve
   or redirect with a documented mapping during cutover.
6. **Manual execution boundary**: the product may recommend trades and moves,
   but it must not submit offers or automate external league actions.

### Migration constraints

- Never migrate the primary local database in place without a backup copy and a
  restore test.
- Preserve raw ingest meaning, league settings, corrections, snapshots, and
  user-owned overrides; derived caches may be rebuilt if their source and
  version are recorded.
- Do not infer a new schema's correctness from row counts alone. Reconcile
  stable keys, selected value hashes, freshness domains, and recommendation
  provenance.
- Keep legacy reads available until the v2 critical journeys pass against a
  realistic copied database.
- Treat incomplete Sleeper history, unavailable stats, and missing dense metrics
  as explicit degraded states, not zeros or silent fallback.

## Causal account of the highest-leverage problems

| Observed problem | Immediate cause | Repeatable failure mode | Durable detection/prevention | Baseline verification |
| --- | --- | --- | --- | --- |
| Two backend tests fail on clean HEAD | Manager action emission and opportunity ranking do not match their acceptance rules | A recommendation can omit an executable trade or outrank a lineup-solving move by raw gap | Scenario-based decision contract tests; rank explanations; fail the gate on contradictory ordering | `uv run pytest -q`: 550 passed, 2 failed |
| Schema is maintained in migrations, runtime DDL, and test SQL | Compatibility was added alongside incremental phases | New table/column works in one startup path and is missing in another | Alembic-only authority plus empty/legacy migration tests and schema hash/contract checks | 25 Alembic versions; `startup_tasks.py`; `test_support/schema_sql*.py` |
| Browser smoke can hang or produce false negatives | `networkidle` waits for HMR; route assertions use fixed timing rather than readiness | A healthy page is marked hung or missing content; browser errors can be hidden by exit status | Use DOM readiness markers, bounded request assertions, and a preview-mode browser job | Existing `browserSmoke.mjs`; custom DOMContentLoaded check passed after readiness waits |
| Format gate fails before formatting begins | Script references undeclared `prettier` executable | Every required quality run stops at a missing tool | Declare and lock the formatter, verify bare command/path/version in CI | `pnpm format`: `prettier: command not found` |
| Local runtime has no process-level health endpoint | Health route was designed around league ingest state | Supervisors and smoke tests cannot distinguish process readiness from league data health | Add `/healthz`, `/readyz`, dependency/source status, and per-league data health separately | `/health` and `/health/` returned 404; `/health/{league_id}` exists |
| Product navigation reflects feature history | Each phase added routes and shell links | Users choose among many destinations without a single current decision path | Rebuild information architecture around Today -> League -> Action; use deep links as projections | 19 frontend route files; five primary global nav items plus league subroutes |

## Current quality score

Scores are 1–5, where 1 is materially unsafe/unusable and 5 is coherent,
verified, and maintainable. These scores describe the committed baseline, not
the dirty overlay and not the proposed target.

| Dimension | Score | Evidence |
| --- | ---: | --- |
| Product coherence | 3 | Clear mission and strong recommendation features, but many peer destinations and phase-shaped surfaces |
| Correctness and data integrity | 2 | 550 passing tests but 2 failures; 43 tables; 25 migrations; triple schema authority |
| Architectural coherence | 2 | 26 domain packages/routers, oversized orchestrators, shell-wide dashboard dependency |
| Maintainability | 2 | 1,929-line dashboard router, 1,235-line frontend type file, repeated contracts and schema setup |
| Testability | 3 | Broad backend suite and browser smoke exist; frontend behavioral coverage is thin and smoke harness is unreliable |
| Security and privacy | 2 | Local-only intent helps, but wildcard CORS with credentials, unauthenticated mutations, and no configured secrets scan |
| UI quality and accessibility | 3 | Strong hierarchy and no observed overflow/console errors on tested desktop routes; narrow and state coverage incomplete |
| Performance | 2 | Root-level summary fetch, heavy orchestration, no budget/retention policy, and known enrichment cost |
| Operability | 2 | Local launcher and ingest history exist; no process health contract, CI workflow, or fresh passing quality evidence |
| Developer experience | 2 | README and commands are useful; format dependency is missing, relative package path is fragile, startup paths diverge |

The Pronto route was **Ready** at `2026-08-01T19:21:51Z`, but correctly marked
the primary workspace dirty and integration-blocked. Its persisted quality
snapshot was stale, with 121 unreviewed findings, 60 high-severity findings, no
finding disposition contract, zero fresh passing gates, and no configured
secrets scan. That evidence is useful for planning but is not a substitute for
the fresh command results above.

## Audit conclusion

The project is a strong candidate for a protected parallel v2, not a blind
rewrite and not a cosmetic cleanup. Preserve the data model's meaning, domain
rules, source adapters, and recommendation evidence. Replace the shell,
contracts, schema authority, and cross-feature orchestration in vertical slices.
The target definition and milestone plan are in `TARGET.md` and `EXEC_PLAN.md`.
