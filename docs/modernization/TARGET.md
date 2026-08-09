# Fantasy v2 Target Definition

Status: accepted implementation target; Fresh Intelligence is the first
end-to-end v2 product slice.

## Target statement

Fantasy v2 is a local-first dynasty football front office that answers one
question quickly and defensibly:

> What is the best move for this team, in this league, right now, and what
> evidence would change that recommendation?

The target is a recommendation-first product, not a collection of analytical
screens. Every recommendation must expose the decision, timing, acceptable
price or action, confidence, freshness, evidence, downside, and next click.
The user remains the final decision-maker and executes all external league
actions manually.

## Product principles

1. **Decision before data.** Lead with the move and its consequence; let the
   user open the supporting model evidence.
2. **League context is the product.** No universal rank or value should appear
   without format, roster, direction, timing, and uncertainty context.
3. **Every claim has provenance.** Show source, observed time, freshness, and
   what is inferred versus directly observed.
4. **Uncertainty is a first-class state.** Low confidence, missing data,
   unsupported format, degraded source, and manual review are visible states,
   not empty strings or silent fallbacks.
5. **One action model, many views.** Dashboard, league briefing, trade, weekly,
   waiver, rookie, manager, and portfolio surfaces render the same canonical
   decision contract.
6. **Local-first and recoverable.** A local DuckDB file is valuable user data;
   refreshes, migrations, exports, and rollback are explicit and auditable.
7. **Calm front-office UI.** The visual system should feel like an excellent
   analyst's briefing: high signal, readable, restrained, and fast to scan.
8. **Human control at the boundary.** Recommendations can prepare a trade or
   waiver move, but never submit or send it.

## Target user journeys and information architecture

### Global navigation

The target has four top-level destinations:

1. **Today** — cross-league prioritized action queue, stale lanes, and a short
   explanation of why each move matters now.
2. **Leagues** — the active league workspace and league switcher.
3. **Portfolio** — cross-league exposure, correlation, hedge, and season trend.
4. **Research** — prospect, market, and historical evidence that is not itself
   an action queue.

Settings, data health, corrections, and source refresh are utility surfaces
available from the workspace chrome, not competing primary destinations.

### League workspace

Every league opens to one briefing page with sections that can be deep-linked:

- **Briefing:** direction, confidence, title window, top three moves, and
  freshness summary.
- **Roster:** playable lineup, replacement gaps, hygiene, injury/usage risk,
  and roster-fit upgrades.
- **Market:** opportunities, trade paths, manager targets, and acceptable deal
  ranges.
- **Draft:** picks, draft-order rule, rookie board, draft room, and draft
  grades.
- **League operations:** rules, corrections, ingest history, unsupported-format
  acknowledgments, and manual refresh.

The destination pages remain deep-linkable, but the information architecture
always shows the current league and the decision context that led there.

### Canonical decision flow

`Today -> decision card -> evidence drawer -> prepared action -> destination workflow -> user confirmation`

Example: Today surfaces “Buy low: Justin Fields because the model is 0.50 above
market and your weekly QB insulation is low.” The user opens evidence, chooses a
counterparty and package, and reaches Trade Lab with a reversible prefill. No
external offer is sent.

### States required on every principal flow

- loading with a clear scope and expected next state;
- empty with a reason and next safe action;
- stale with the affected source and a refresh option;
- degraded with partial results and omitted evidence named;
- unsupported format with the exact rule requiring acknowledgment;
- error with retry, preserved user inputs, and a diagnostic run ID;
- success with the resulting persisted state and freshness timestamp;
- keyboard focus, labels, disabled semantics, and mobile layout.

## Visual and interaction direction

Keep the best parts of the current system—strong typography, restrained blue
accent, compact action cards, and visible confidence/freshness tags—but shift the
metaphor from “terminal cockpit” to “analyst briefing.”

### Direction

- Use a quiet neutral canvas and one strong accent family for action state.
- Make the primary action sentence the largest object in a decision card.
- Use color for urgency, confidence, source health, and direction only; do not
  turn every label into a badge.
- Replace repeated terminal breadcrumbs and footer status with compact context
  chrome: current league, last refresh, and source health.
- Use expandable evidence drawers for model dimensions, similar-player context,
  and historical support.
- Keep one primary CTA per card. Secondary actions become text links or menu
  items.
- Prefer two-column desktop layouts that collapse to one column without hiding
  the action or evidence on mobile.
- Treat data density as a hierarchy problem, not a reason to add more cards.

### Representative screens for the first visual review

Before propagating the system, build only:

1. Today with three decision cards and a stale-data lane;
2. League Briefing with direction, lineup gap, and next move; and
3. Trade preparation with evidence drawer, deal range, and confirmation boundary.

These screens must be reviewed visually at 375px, 768px, and 1440px before the
rest of the routes inherit the system.

## Target architecture

The existing Python and React choices remain. They are familiar, fast enough for
the local scale, and not the root problem. The target changes boundaries and
contracts before considering a framework replacement.

### Backend layers

1. **Domain** — pure models and rules for league format, roster, asset, market,
   decision, draft, and portfolio concepts. No FastAPI, DuckDB, or HTTP imports.
2. **Application** — vertical use cases such as `BuildToday`, `BuildLeagueBrief`,
   `PrepareTrade`, `RefreshLeague`, `BuildWeeklyEdge`, and `GradeDraft`. Each
   use case owns orchestration and returns a stable read model.
3. **Ports** — typed interfaces for league source, market source, historical
   stats, clock/calendar, persistence, and event/log emission.
4. **Adapters** — Sleeper, FantasyCalc, nflreadpy/nfl-data-py, CSV import, and
   DuckDB implementations. External syntax ends here.
5. **API** — thin FastAPI routers that validate input, invoke one use case, map
   errors to a stable envelope, and expose OpenAPI contracts.

Dependency direction is inward: adapters depend on ports; application depends
on domain and ports; API depends on application; domain depends on nothing
external. A module may not reach around its use case into another feature's
repository.

### Frontend layers

1. **App shell** — route context, theme, responsive navigation, error boundary,
   process/source status; no feature data fetches.
2. **Design system** — typography, surface, button, badge, drawer, table, state
   panels, and responsive primitives.
3. **Workspace context** — selected league, roster, calendar state, and freshness
   summary from URL plus a small server-state query.
4. **Feature flows** — Today, Briefing, Roster, Market, Draft, Portfolio, and
   Research. Each owns route composition and presentation of use-case read
   models.
5. **API client/contracts** — one generated or schema-derived contract layer,
   query keys, mutation invalidation, and error decoding.

Routes should be composition roots, not data/logic containers. The global shell
must not fetch dashboard data just to render navigation.

### Canonical decision contract

The target `DecisionCard` shape should contain at least:

- stable ID and decision lane;
- league/roster/asset/manager scope;
- plain-language action and target outcome;
- urgency and timing window;
- confidence band and score explanation;
- acceptable price/range or concrete next action;
- risk/downside and what would invalidate the thesis;
- evidence list with source, observed time, freshness, and provenance type;
- capability state (`ready`, `stale`, `degraded`, `blocked`, `manual_review`);
- destination and reversible prefill payload;
- model version and input snapshot identifiers.
- trigger event IDs and the time the decision last changed;
- an impact summary naming affected assets and before/after deltas.

Existing recommendation, opportunity, action, weekly, waiver, hygiene, pick,
and trade payloads should map into this contract rather than each inventing
another card shape.

## Data ownership and state management

### Source-of-truth policy

- Raw source observations and user corrections are durable facts.
- Derived valuations, recommendations, profiles, and read models are rebuildable
  artifacts with model/input versions.
- Freshness and gap records describe the validity window of a fact or artifact.
- Snapshots are immutable historical evidence; current read models are not
  snapshots.
- The source of schema truth is Alembic. Runtime startup must verify the schema,
  not silently create a second schema authority. Test databases must be created
  by migrations or by a generated schema fixture that is checked against them.

### Frontend state

- React Query owns server state and cache invalidation.
- URL search params own shareable filters, league, roster, manager, player, and
  trade prefill context.
- Component state owns transient drawers, tabs, and form drafts.
- No global state store is introduced unless a measured cross-route workflow
  requires it.

### Refresh semantics

Every refresh operation returns a run ID and a structured result containing:
source outcomes, records affected, gaps, derived artifacts rebuilt, freshness
domains updated, and partial/degraded status. The UI should never show “synced”
when one required source failed.

### Fresh intelligence and consequence graph

Today is the landing page and daily operating loop. External evidence is stored
as immutable observations with fetched, observed, effective, and coverage times,
then normalized into verified football events. Only confirmed events may change
canonical projections. Watch, conflicted, expired, and manual-review events stay
explicit and cannot silently create confirmed actions.

Sources run public-first: structured Sleeper/FantasyCalc/nflreadpy adapters,
configured public HTTP sources, a guarded backend Playwright fallback, then
manual public-link analysis. Browser content is untrusted evidence. Public
fetching validates DNS/IP and redirects, respects source controls, and never
bypasses authentication, paywalls, CAPTCHAs, or anti-bot gates.

Each confirmed event rebuilds only affected player, teammate, ownership,
manager-need, pick-trajectory, waiver/trade/weekly, and portfolio scopes. Stored
impacts include causal deltas, confidence, model/input version, and invalidation.
The prepared brief ranks confirmed actionable consequences before a separate
Watch lane and never performs the external action.

## API, integrations, errors, and observability

- Keep the public API local and versioned around use-case read models, not table
  shapes. Preserve old deep links with redirects or a short-lived adapter during
  migration.
- Use a consistent error envelope with stable code, user message, safe detail,
  retryability, run ID, and affected scope.
- Add `/healthz` for process health and `/readyz` for dependency/schema health;
  keep `/health/{league_id}` as a data-freshness projection.
- Bind to `127.0.0.1` by default. Restrict CORS to the configured frontend
  origin; do not use wildcard origins with credentials.
- Put Sleeper/FantasyCalc/nflreadpy behavior behind ports with source-specific
  retry, timeout, rate-limit, and partial-result policies.
- Emit structured logs for refresh start/finish, source outcome, derived
  rebuild, degraded fallback, migration, and user mutation. Include run ID,
  league ID, source, model version, and duration.
- Keep external API credentials out of the repository. The current public
  integrations do not require auth for the documented reads; any future secret
  must be introduced only with an explicit credential plan.

## Testing strategy

### Required gates

1. `uv run pytest` for backend domain, application, integration, and migration
   fixtures.
2. Frontend typecheck, lint, format, build, and component/contract tests.
3. Playwright acceptance for Today -> Briefing -> prepared Trade, plus weekly,
   waiver, rookie, manager, and portfolio paths.
4. Accessibility checks for keyboard traversal, focus, labels, contrast, and
   reduced motion on representative screens.
5. Migration tests from empty schema and a copied realistic current database,
   including row/key reconciliation and rollback restore.
6. A source-degradation matrix covering timeouts, 404/missing weeks, partial
   data, stale domains, and unsupported format rules.
7. A performance budget for initial shell, Today data readiness, and largest
   decision route; record query count and duration in browser checks.

Tests should be scenario-named and decision-oriented. A test should explain
what a user is protected from—e.g. “lineup-solving buy outranks raw market gap”
or “failed Sleeper week remains visibly stale”—rather than only asserting a
repository method result.

## Deployment and migration approach

The app remains local-only in v2. The development and release lane becomes:

1. verify tools and dependencies;
2. back up/export the current DuckDB file;
3. run migrations against a copied database;
4. run source/data reconciliation and derived rebuild;
5. run the full local validation ladder;
6. start backend and frontend with explicit readiness output; and
7. preserve the prior DB and legacy branch until the cutover checkpoint is
   accepted.

The first v2 cutover should read legacy data through a deliberate import adapter
into a versioned canonical schema. It should not try to preserve every derived
cache table as a permanent compatibility surface. Raw observations, settings,
corrections, snapshots, and stable identity mappings are migrated first;
derived artifacts are rebuilt and labeled with the v2 model version.

Rollback is restoring the pre-cutover DB copy and restarting the legacy branch.
No migration may rely on an irreversible destructive operation without an
export and a tested restore. After two successful refresh cycles and critical
journey verification, old code can be deleted in a separate cleanup milestone.

## Dependencies: retain, add, remove

### Retain

- Python, FastAPI, Pydantic, SQLAlchemy/Alembic, DuckDB, and the current source
  adapters unless a measured issue proves otherwise.
- React, TypeScript, Vite, TanStack Router, and React Query.
- Playwright for browser acceptance.

### Add only when justified

- A declared formatter (Prettier or the repository's chosen equivalent) because
  the current required command is missing its executable.
- Schema-derived API types or OpenAPI generation to eliminate manual response
  drift, with a checked-in generation command.
- A lightweight accessibility assertion tool if the browser harness cannot
  cover the required checks itself.

### Remove or consolidate during migration

- Runtime schema compatibility DDL once legacy migration is complete.
- Duplicated frontend card/type contracts after the canonical decision contract
  is adopted.
- Obsolete route aliases, feature flags, old caches, and dependencies only
  after consumers are moved and deletion is verified.
- Any formatter/quality script that is not reproducible from a clean install.

## Explicit non-goals

- No hosted multi-user product or authentication system in this v2.
- No automated trade, waiver, or league-action submission.
- No universal rankings surface replacing league context.
- No user-authored model-weight editor in the first v2 cutover.
- No forced preservation of internal module names or old route composition.
- No migration of every derived cache as durable source data.
- No new framework adoption for novelty; any replacement requires measured
  benefit and a bounded migration.

## Target quality bar

The target scores below are acceptance goals, not claims about current state.

| Dimension | Target | Meaning of success |
| --- | ---: | --- |
| Product coherence | 5 | One Today -> League -> Action flow with research and utility clearly separated |
| Correctness and data integrity | 4 | Canonical schema, explicit degraded states, verified migrations, no known P0/P1/P2 defects |
| Architectural coherence | 4 | Domain/application/adapter/API boundaries are enforced and routes are thin |
| Maintainability | 4 | Feature ownership is clear; high-blast-radius files are split; obsolete paths removed |
| Testability | 4 | Decision scenarios, contracts, migrations, browser journeys, accessibility, and failure states are covered |
| Security and privacy | 4 | Loopback defaults, explicit CORS, mutation boundaries, backup discipline, secrets gate |
| UI quality and accessibility | 4 | Calm hierarchy, responsive states, keyboard path, focus, labels, contrast, and no unexplained console errors |
| Performance | 4 | Shell is data-light, decision reads are bounded, query and bundle budgets are measured |
| Operability | 4 | Process/readiness/data health are distinct; refresh runs are attributable and recoverable |
| Developer experience | 4 | Clean install, one documented start path, one migration authority, reproducible quality ladder |

## Decisions that genuinely need human product judgment

Defaults are proposed so implementation can continue without low-value pauses.
Only these five decisions should be reviewed before implementation expands:

1. **Primary landing emphasis (default: Today).** Should the app always open on
   the cross-league action queue, or on the last-used league briefing?
2. **Research placement (default: utility under Draft/Market plus a Research
   index).** Should the historical prospect lab be a top-level destination in
   v2 or remain subordinate to draft decisions?
3. **Refresh policy (default: explicit user refresh with optional dev auto-
   refresh disabled by default).** Should local startup ever call external
   Sleeper/FantasyCalc sources automatically?
4. **Legacy depth (default: migrate all durable facts and critical snapshots;
   rebuild derived artifacts).** Which historical derived outputs, if any, must
   remain byte-for-byte inspectable after cutover?
5. **Visual direction (default: analyst briefing).** Approve the calmer briefing
   direction before it is applied beyond the three representative screens.
