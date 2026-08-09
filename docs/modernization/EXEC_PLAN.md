# Fantasy v2 Execution Plan

Status: Milestones 0–8 implemented and verified in the protected
`codex/rebuild-gpt56` worktree. The current fleet-normalization task explicitly
authorizes the local fold into `dev`; publish, deploy, and default-DB switch
remain separately gated.

## Strategy choice

Choose **B: parallel v2 implementation with progressive migration**.

### Why B

- A deep in-place refactor would keep the current shell, route contracts, and
  triple schema authority alive while trying to untangle them.
- A clean rewrite would risk losing valuable league-specific rules, corrections,
  snapshots, and historical model meaning.
- A protected parallel v2 can replace the application shell and boundaries while
  importing durable facts from a copied DuckDB file and keeping the current app
  available for comparison until critical journeys are proven.

The blast radius is intentionally large inside a milestone, but each milestone
ends in a runnable vertical slice with explicit tests and browser evidence.

## Operating guardrails

- Work only on `codex/rebuild-gpt56` until the authorized local fold; do not
  publish, deploy, or switch the default DB without a separate gate.
- Treat `TARGET.md` as the product definition and this file as executable state.
- Update `PROGRESS.md` at each milestone boundary.
- Never point v2 at the user's primary database during development or migration
  tests; use a copied or disposable database.
- Preserve unrelated dirty work and do not reset, stash, delete, push, or
  publish without explicit authorization. The fleet-normalization request is
  the explicit authorization for the local fold of this protected branch.
- Use Alembic as the only schema authority after Milestone 1.
- A milestone is incomplete if a required check fails without a disposition.
- Keep a short-lived legacy adapter only when it directly enables migration;
  delete it after consumers move.
- No trade/waiver/league action may cross the local app boundary automatically.

## Milestone 0 — Protected baseline and verification harness

**Status (2026-08-01): implemented in `codex/rebuild-gpt56`.** The protected
worktree has reproducible formatting, explicit browser readiness and state
fixtures, health/readiness probes, and disposable DuckDB copy/restore tooling.
The former manager-action baseline failure was resolved in Milestone 5; the
complete backend suite now passes.

**Objective**

Make the baseline reproducible and the v2 branch safe to change.

**Affected directories and systems**

`docs/modernization/`, frontend quality scripts, browser harness, local DB
backup tooling, and repository-local development commands. No product behavior
should change until the baseline artifacts are accepted.

**Dependencies**

None. This audit is the starting point.

**Behavior to preserve**

Current install, startup, dashboard summary, principal deep links, and the
manual execution boundary.

**Behavior intentionally changed**

Make missing tools and browser readiness fail explicitly rather than produce
false green results. Add process health/readiness probes if the existing API
contract allows it.

**Tests and browser checks**

- Re-run the clean baseline tests and record dispositions for the two failures.
- Make the format command reproducible from a clean install.
- Replace `networkidle` dependence with explicit readiness markers and bounded
  API/request checks.
- Add empty, stale, degraded, and error fixture routes to the browser harness.

**Data migration/rollback**

Create a documented DB copy/restore command and an inventory manifest of stable
tables/keys. Rollback is deleting only the disposable copy and returning to the
baseline branch.

**Completion criteria**

Clean install passes the documented tool ladder; browser smoke exits nonzero on
real errors and has no HMR hang; baseline failures have owner/disposition;
baseline screenshots and DB manifest are stored.

**Old code to delete**

None yet. Do not hide the two baseline backend failures.

**Likely failure modes**

Missing network access, local package path issues, stale DB copy, browser binary
availability, and tests that implicitly depend on the developer's environment.

## Milestone 1 — New shell, contracts, and design foundation

**Status (2026-08-02): implemented and browser-verified.** The shell is
page-owned, the canonical `DecisionCard` contract and state panels are in use,
and Today, Leagues, Research, Operations, League Briefing, and Trade
Preparation are reachable without root-level dashboard fetching.

**Objective**

Build the thin v2 app shell and three representative screens: Today, League
Briefing, and Trade Preparation. Establish the design system and canonical
`DecisionCard` contract before porting every feature.

**Affected directories and systems**

New frontend shell/design-system/feature modules; backend read-model contract
types and a compatibility mapper for current action/opportunity payloads;
OpenAPI/type generation or a checked-in contract adapter.

**Dependencies**

Milestone 0 and the five target decisions, especially landing emphasis and
visual direction.

**Behavior to preserve**

Current dashboard Top Moves meaning, direction/freshness labels, trade prefill
context, and manual execution boundary.

**Behavior intentionally changed**

Top-level information architecture becomes Today -> League -> Action; global
shell stops fetching dashboard data on every route; terminal labels and repeated
status chrome are reduced.

**Tests and browser checks**

- Contract fixtures map current actions into `DecisionCard`.
- Component tests cover loading, empty, stale, degraded, blocked, error, and
  ready states.
- Browser screenshots at 375/768/1440 for all three screens.
- Keyboard traversal and focus assertions for filters, drawers, and primary CTA.

**Data migration/rollback**

Read legacy tables through adapters only. No persistent schema change. Rollback
is removing the v2 shell and returning to the baseline branch.

**Completion criteria**

Three screens look coherent at all three widths, all decisions expose
confidence/freshness/evidence, no feature data is fetched by the root shell,
and the old app still runs from the baseline worktree.

**Old code to delete**

Only duplicated prototype components created within this milestone. Do not
delete existing feature routes yet.

**Likely failure modes**

Visual system overreach, a contract that is too generic for trade/draft flows,
and accidentally hiding useful model evidence behind the new hierarchy.

## Milestone 2 — Canonical data truth and refresh vertical slice

**Status (2026-08-02): implemented and migration-verified.** Refresh, freshness,
gap, health/readiness, and Alembic revision-025 paths run against a copied DB;
the primary DB remains on revision 024.

**Objective**

Rebuild `RefreshLeague` end to end: source ingest -> durable facts -> freshness
and gaps -> derived read models -> Today/Briefing data health.

**Affected directories and systems**

Backend domain/application/ports/adapters/persistence packages; Alembic schema;
refresh routes; test DB setup; frontend data-health and refresh UI.

**Dependencies**

Milestone 0 for DB backup and Milestone 1 for shell/contract states.

**Behavior to preserve**

Sleeper league/roster/transaction/pick/draft meaning, corrections, freshness
domains, explicit gap behavior, and downstream artifact recompute.

**Behavior intentionally changed**

One canonical schema authority replaces runtime/test triple-write DDL. Refresh
returns a structured run result and never labels a partial source run as fully
synced.

**Tests and browser checks**

- Empty DB migration and upgrade-from-current-copy tests.
- Source timeout, 404, missing-week, malformed-data, and partial-recompute
  scenarios.
- Stable key/value reconciliation for leagues, rosters, players, transactions,
  corrections, and snapshots.
- Browser refresh success, stale, degraded, and error paths.

**Data migration/rollback**

Create v2 canonical tables beside legacy tables in a copied DB. Import durable
facts, compare counts/keys/sample hashes, rebuild derived artifacts, and keep a
restore manifest. Never drop legacy tables in this milestone.

**Completion criteria**

Two seeded leagues can refresh in the copied DB; every source outcome is
visible; migrations run from empty and legacy copies; no runtime DDL is needed;
Today and Briefing show truthful freshness.

**Old code to delete**

No legacy tables or adapters yet. Delete only duplicate migration/test helpers
that have been proven unused.

**Likely failure modes**

DuckDB locking/concurrency, source API drift, duplicate identity mapping,
partial writes, and derived caches being mistaken for source truth.

## Milestone 3 — Fresh Intelligence and League Impact Graph

**Status (2026-08-02): vertical slice implemented and accepted in
`codex/rebuild-gpt56`.**

**Objective**

Turn current public football evidence into verified events, scoped league
consequences, and a prepared morning brief. The product unit is `external event
-> NFL role/value change -> ownership/manager/pick impact -> best reversible
move`, not an isolated headline.

**Affected directories and systems**

Freshness persistence, structured/public/browser source adapters, optional
narrative extraction, event/evidence and impact tables, the Today route,
generated API contracts, local scheduling template, and consequence tests.

**Dependencies**

Milestones 1–2 for the Today shell, canonical truth, migrations, and explicit
degraded states.

**Behavior to preserve**

Sleeper/FantasyCalc/nflreadpy meanings, last confirmed snapshots after failure,
local-only storage, and the human execution boundary for every trade, waiver,
lineup, and league action.

**Behavior intentionally changed**

Freshness requires a parsed current result or authoritative empty result.
Sources use a structured -> public HTTP -> guarded browser -> pasted-link
ladder. Only confirmed events drive canonical consequences; watch/conflicted
claims remain scenarios. Today becomes the prepared landing page.

**Tests and browser checks**

- Truth regressions for independent Sleeper freshness and zero-row market data.
- Adapter failures for schema drift, 404/429, timeouts, redirects, anti-bot,
  malformed content, prompt injection, cached content, and partial runs.
- Event dedupe, corroboration, conflicts, expiry, and review audit history.
- A two-league injury scenario proving direct, teammate, manager-need, pick,
  waiver/trade/portfolio effects and excluding an unaffected league.
- Fixed morning bundle and partial outage preservation.
- Today, evidence/impact detail, URL analysis, review, and prepared action at
  375px, 768px, and 1440px.

**Data migration/rollback**

Alembic creates source-run, immutable observation, event/evidence, rebuildable
impact, daily brief/item, review, and feedback tables beside legacy data. Test
empty and realistic copied DuckDB upgrades. Raw bodies remain in an ignored
seven-day cache. Rollback restores the copy; no legacy table is dropped.

**Completion criteria**

The scheduled command is idempotent; every actionable external fact has a
meaningful league consequence; every fact exposes source and invalidation;
partial outages preserve and label the last good brief; unchanged pages bypass
extraction; no action is submitted externally.

**Old code to delete**

None until later milestone consumers migrate. Remove only duplicate freshness
or response-shape helpers proven unused.

**Likely failure modes**

Source drift, rate limits, unresolved identities, stale-but-new fetches,
over-broad consequence fanout, DuckDB locks, anti-bot responses, and model
output being mistaken for verification.

## Milestone 4 — League Briefing and roster decision slice

**Status (2026-08-02): implemented and browser-verified.** League Briefing
combines direction, lineup leverage, roster context, freshness, evidence, and
an explicit roster-moves destination with blocked/no-roster handling.

**Objective**

Make the league briefing answer “what are we and what should we do next?” from
direction through lineup gap, roster hygiene, weekly edge, and prepared move.

**Affected directories and systems**

League/roster/lineup/weekly application use cases; read-model projections;
frontend Briefing/Roster feature routes and shared decision components.

**Dependencies**

Milestones 1–2.

**Behavior to preserve**

Team scorecards, direction alternates, title-window/lineup scoring, roster
hygiene, taxi/IR settings, weekly context, and injury/usage/schedule freshness.

**Behavior intentionally changed**

These outputs become one briefing narrative with explicit evidence and a small
number of next moves instead of parallel panels with separate language.

**Tests and browser checks**

- Direction/lineup/hygiene/weekly decision scenario tests.
- Test a real lineup gap, no replacement, stale source, and unsupported roster
  rule.
- Browser journey from Today to Briefing to roster move on desktop/mobile.
- Verify keyboard focus and screen-reader labels on action cards and drawers.

**Data migration/rollback**

Read v2 canonical facts and rebuild derived read models. No deletion. Rollback
is a view/route switch and copied-DB restore.

**Completion criteria**

Every active league has a briefing with a confidence-bearing next move or a
truthful blocked/empty state; existing current-value calculations reconcile for
sample rosters; v2 remains runnable at the boundary.

**Old code to delete**

After route parity is proven, remove only duplicate briefing aggregators and
unused compatibility view mappers.

**Likely failure modes**

Narrative duplication, false certainty from stale weekly data, and route
prefills losing league/roster context.

## Milestone 5 — Market, manager, and trade preparation slice

**Status (2026-08-02): implemented and backend/browser-verified.** The canonical
decision endpoint maps manager/market actions, the manager prefill contract now
selects a deterministic primary roster when no owner is configured, and Trade
Preparation retains a manual-only execution boundary.

**Objective**

Rebuild the highest-value action loop: model-vs-market signal -> manager target
and pitch -> acceptable package -> Trade Preparation -> manual execution.

**Affected directories and systems**

Market, trade, manager profiling, Edge Radar, recommendation/application
use-cases, trade routes, search APIs, and frontend Trade/Manager flows.

**Dependencies**

Milestones 1–4; canonical DecisionCard; baseline manager-action failure must be
resolved or explicitly re-scoped.

**Behavior to preserve**

Market gap classifications, roster/direction fit, manager tendencies and pitch
angles, package builder, reroutes, pick assets, multi-team sidecar evaluation,
and no-submit boundary.

**Behavior intentionally changed**

All market and manager recommendations share one decision contract and one
prepared-action boundary. Trade Lab becomes a destination for an explicit card,
not a separate competing starting point.

**Tests and browser checks**

- Reproduce and fix the clean-baseline manager action failure.
- Contract tests for buy/sell/hold, counterparty, reroute, pick, and multi-team
  paths.
- Browser Today -> evidence -> manager -> prepared trade; verify no network
  mutation beyond allowed local writes and no external submission affordance.

**Data migration/rollback**

Import market snapshots and manager history as source evidence; rebuild profiles
and recommendations with a v2 model version. Preserve legacy snapshots. Restore
from copied DB if scoring parity or identity mapping fails.

**Completion criteria**

A real seeded opportunity produces a correct, explainable, reversible trade
prefill with manager evidence; a no-fit case is blocked or degraded honestly;
baseline and v2 values are reconciled for agreed fixtures.

**Old code to delete**

Remove legacy action aggregators, duplicate market-gap card mappers, and stale
trade route hydration after all consumers are moved.

**Likely failure modes**

Wrong roster perspective, stale market source, over-broad manager inference,
multi-team package ambiguity, and accidental external mutation.

## Milestone 6 — Waiver and weekly execution slice

**Status (2026-08-02): implemented and browser-verified.** Today decision cards
route to the existing legal waiver/weekly surfaces, whose stale, blocked, empty,
and freshness-aware states remain explicit.

**Objective**

Make weekly and waiver decisions executable from freshness-aware lineup gaps,
with legal roster moves, FAAB guidance, and explicit blocked states.

**Affected directories and systems**

Waiver, weekly, lineup-gap, correction, and action use cases; frontend weekly,
waiver, roster, and Today destinations.

**Dependencies**

Milestones 2–5.

**Behavior to preserve**

Start/sit legality, availability/injury handling, FAAB ranges, position caps,
waiver recommendations, roster hygiene, orphan intake, and freshness notes.

**Behavior intentionally changed**

Weekly and waiver outputs use the same urgency/confidence/evidence language and
are ordered by roster consequence rather than source-specific ranking alone.

**Tests and browser checks**

- Legal/illegal lineup swap cases, no opponent, bye, inactive/free-agent, and
  missing stat samples.
- FAAB cap and stronger-anchor cases.
- Browser narrow-width path through a stale weekly source and a successful
  prepared add/drop move.

**Data migration/rollback**

Derived weekly/waiver artifacts are rebuilt. User corrections and manual
exceptions are imported before any derived write. Rollback restores facts and
rebuilds legacy caches.

**Completion criteria**

The user can identify a lineup consequence, inspect source freshness, and reach
an explicit manual action with legal roster context; partial source failure is
visible and does not masquerade as zero.

**Old code to delete**

Delete duplicate weekly/waiver card presenters and stale route-only query
helpers after parity tests pass.

**Likely failure modes**

Fantasy-calendar edge cases, position/slot legality, contradictory stale
domains, and incorrect owner perspective.

## Milestone 7 — Draft, rookie, and prospect decision slice

**Status (2026-08-02): implemented and browser-verified.** Draft Room, Rookie
Board, draft grades, startup, and research routes remain available as
league-aware destinations from the v2 shell and research surface.

**Objective**

Rebuild pick valuation, draft-order rules, rookie board, draft room, draft
grades, startup mode, and prospect evidence as one draft decision workflow.

**Affected directories and systems**

Picks, rookie, rookie-pick profiles, prospect, startup, draft-grade use cases;
schema/read models; frontend Draft and Research features.

**Dependencies**

Milestones 2–4; human decision on Research placement.

**Behavior to preserve**

League-specific draft order, pick timing, class strength, manager draft
tendencies, historical feature/model outputs, comps, hit rates, risk bands, and
format warnings.

**Behavior intentionally changed**

Draft research is attached to the roster/league decision and does not require a
separate universal board mental model.

**Tests and browser checks**

- Regression fixtures for every draft-order rule already named in the roadmap.
- Pick/model/market gap and rookie-fit scenarios.
- Browser clock decision, trade-back, best-for-roster, and blocked unsupported
  format cases.

**Data migration/rollback**

Import durable draft selections and historical prospect facts; rebuild model
outputs with versioned inputs. Keep legacy raw prospect tables until parity is
proven.

**Completion criteria**

The same pick/prospect can produce intentionally different guidance by league,
calendar, and roster; every surfaced value cites its rule/source/freshness; no
universal rank is presented as a final answer.

**Old code to delete**

Remove obsolete board-only aggregators and duplicated pick card types after
route parity.

**Likely failure modes**

False precision from thin historical samples, stale draft capital, rule drift,
and mixing current value with at-time grade semantics.

## Milestone 8 — Portfolio, operations, and full cutover rehearsal

**Status (2026-08-02): rehearsal complete; cutover withheld.** Portfolio and
Operations remain page-owned, health and schema readiness are separate probes,
the copied DB migrated and restored at revision 025, and the full frontend,
backend, and three-viewport browser ladder passed. No primary DB switch or
external action was performed.

**Objective**

Complete portfolio exposure/retrospectives, settings/corrections, data health,
backup/restore, and deployment documentation; rehearse the full cutover.

**Affected directories and systems**

Portfolio, snapshots, corrections, trust, operations/settings UI, CLI/dev
launcher, migration/export scripts, CI/quality configuration, docs.

**Dependencies**

Milestones 0–7 and all human decisions.

**Behavior to preserve**

Exposure, correlated risk, snapshots, retrospective evidence, corrections,
format acknowledgments, manual refresh, and local-only deployment.

**Behavior intentionally changed**

Operational state becomes explicit: process health, schema readiness, source
freshness, and per-league data health are separate projections. Startup refuses
incompatible schemas rather than silently repairing them.

**Tests and browser checks**

- Full backend/frontend/browser/accessibility/performance ladder.
- Fresh install from documented commands.
- Backup, restore, migration forward, and rollback rehearsal on a realistic
  copied DB.
- Search for stale flags, routes, imports, old schema helpers, disabled checks,
  and TODOs.

**Data migration/rollback**

Generate final export/reconciliation manifest, preserve legacy DB and branch,
run v2 against a fresh copy, and record restore time. Rollback remains a tested
restore plus legacy startup.

**Completion criteria**

All critical journeys pass; no confirmed P0/P1/P2 findings remain without an
explicit accepted disposition; docs match the implementation; rollback is
reproducible by a second clean invocation.

**Old code to delete**

Only after cutover approval: legacy routers, route tree, duplicate schema DDL,
compatibility mappers, unused dependencies, flags, tests, and documentation.

**Likely failure modes**

Migration key loss, hidden legacy consumers, data freshness mislabeling, local
filesystem permissions, and deleting a fallback before the two-cycle proving
period is complete.

## Cutover and rollback strategy

1. Freeze a named baseline DB copy and export manifest.
2. Run v2 migration/import on a new copied file; never overwrite the primary.
3. Compare durable table counts, stable keys, selected value hashes, correction
   records, and snapshot anchors.
4. Run two refresh cycles with one normal source response and one induced source
   degradation. Verify the UI tells the same truth in both cases.
5. Run the complete quality and browser ladder from a fresh shell.
6. Review Today, Briefing, Trade Preparation, weekly/waiver, draft, manager,
   portfolio, and operational states at mobile/tablet/desktop.
7. With explicit human approval, switch the local launcher/default DB pointer to
   v2. Retain legacy branch and pre-cutover DB.
8. After the proving period, delete old code in a separate commit/milestone and
   rerun the full ladder.

Rollback is a deliberate restart on the preserved legacy branch and database
copy. Any migration that cannot be rolled back this way is not ready for
cutover.

## Current-to-target scorecard

| Dimension | Current | Target | Acceptance evidence |
| --- | ---: | ---: | --- |
| Product coherence | 3 | 5 | Today/League/Action flow tested across critical journeys |
| Correctness and data integrity | 2 | 4 | Green decision suite, explicit degraded states, migration reconciliation |
| Architectural coherence | 2 | 4 | Import-direction checks and thin routes/use cases |
| Maintainability | 2 | 4 | No oversized cross-feature orchestrators in new path; obsolete code removed |
| Testability | 3 | 4 | Scenario contracts, migration tests, browser/accessibility/failure coverage |
| Security and privacy | 2 | 4 | Loopback/CORS/mutation policy and secrets gate verified |
| UI quality and accessibility | 3 | 4 | Three representative screens reviewed at 375/768/1440 and keyboard-tested |
| Performance | 2 | 4 | Shell/data-read budgets and bounded enrichment verified |
| Operability | 2 | 4 | `/healthz`, `/readyz`, data health, run IDs, backup/restore, fresh gates |
| Developer experience | 2 | 4 | Clean install/start/migrate/test path works from a fresh checkout |

## Human review gate before implementation

Review only the target product direction, data migration policy, architecture
boundaries, navigation structure, and visual direction. Once those are accepted,
the lead implementation thread may proceed autonomously through ordinary
ambiguity and milestone failures, stopping only for unrecoverable data loss,
irreversible external action, missing non-substitutable credentials, or a new
large-impact product choice.
