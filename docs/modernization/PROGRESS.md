# Fantasy v2 Modernization Progress

Last updated: 2026-08-08

## Current phase

**Milestones 0–8 — implemented and verified in the protected worktree.**

The implementation was subsequently split into atomic commits on this branch:
fresh-intelligence backend (`cdae8e7`), recommendation-first frontend
(`d56735a`), generated-route gate exception (`30cef5b`), frontend formatting
contract (`17b284e`), and operations documentation (`5410d6f`). The local fold
into canonical `dev` is authorized by the fleet-normalization task; live
remote publication remains gated on a successful provider check.

The protected worktree is `/Users/jakyeamos/projects/Fantasy/.worktrees/gpt56-v2`
on branch `codex/rebuild-gpt56`, based on commit
`ec614a53a7614f6375277082881cb4899eeb695b`.

## Completed

- [x] Preserved the pre-existing dirty `dev` checkout.
- [x] Ran the repository-local Pronto route. It was Ready at
  `2026-08-01T19:21:51Z`; the primary workspace was correctly reported dirty
  and integration-blocked.
- [x] Created the isolated v2 worktree and branch.
- [x] Installed locked backend and frontend dependencies in the isolated
  environment.
- [x] Resolved the manager-action owner-perspective failure by making the
  unconfigured fallback deterministic by first roster ID, and aligned the
  dashboard and portfolio projections.
- [x] Ran the complete backend suite: **584 passed in 88.48s**.
- [x] Made frontend formatting reproducible with the declared Prettier 3.8.1
  tool and config; lint, typecheck, build, dead-code, format, and render checks
  pass.
- [x] Started FastAPI and Vite against a copied DuckDB database.
- [x] Verified dashboard summary, OpenAPI generation, principal API requests,
  and seeded data coverage.
- [x] Reworked browser smoke to use explicit DOM readiness, fresh pages per
  route, and empty/stale/degraded/error API fixtures; 13 routes plus the
  high-confidence interaction pass.
- [x] Captured and inspected baseline dashboard and opportunity screenshots.
- [x] Wrote `AUDIT.md`, `TARGET.md`, and `EXEC_PLAN.md`.
- [x] Added `/healthz` and DB-backed `/readyz` probes, plus a disposable
  DuckDB copy/restore command and inventory manifest.
- [x] Repaired source-result freshness so failed/zero-row refreshes preserve and
  visibly degrade the last confirmed snapshot.
- [x] Added Alembic-managed source runs, immutable observations, verified
  events/evidence, rebuildable league impacts, daily briefs/items, review audit,
  and local feedback.
- [x] Added nflreadpy, local Sleeper/FantasyCalc, guarded public HTTP/browser,
  manual URL, deterministic extraction, and optional OpenAI-compatible adapters.
- [x] Added the affected-scope league consequence graph and deterministic Today
  brief, including a seeded two-league injury scenario and outage preservation.
- [x] Added the v2 intelligence API, schema-generated frontend types, Today
  briefing/review/feedback UI, and scheduled backend command.
- [x] Upgraded an empty DuckDB and a realistic copied revision-024 database to
  revision 025; reconciled eight legacy tables with no row-count drift and ran
  a repeat scheduled smoke without touching the primary database. Repeated
  fetches deduplicated observations/events; advancing source-health timestamps
  produced distinct immutable brief revisions, while exact-content publication
  remains idempotent. Evidence:
  `evidence/fresh-intelligence-migration.json`.
- [x] Passed live browser acceptance for Today, prepared actions, evidence and
  invalidation, feedback, Watch, and confirm/reject review at 375px, 768px, and
  1440px with no horizontal document overflow.
- [x] Reproduced and fixed the DuckDB read-after-review connection race by
  serializing request-scoped connection lifetimes; the regression test and a
  live confirm/reject refetch both pass without a 500.
- [x] Added the canonical `/v2/decisions` adapter and page-owned v2 shell
  surfaces for Today, Leagues, Research, Operations, League Briefing, and
  Trade Preparation; Trade Preparation remains manual-only.
- [x] Ran focused decision/health/intelligence/command-center/portfolio
  coverage: **44 passed**.
- [x] Ran the live route/state/interaction browser rehearsal at **375px,
  768px, and 1440px**: 16 routes per viewport, no horizontal overflow, and no
  unhandled browser errors.
- [x] Migrated a copied revision-024 DuckDB to revision 025, restored it to a
  second copied file, and verified matching SHA-256 values. The copied DB has
  53 tables and 2 leagues; the primary remains revision 024 with its original
  SHA-256.

The former tooling findings are resolved in this milestone:

- `pnpm format` now runs from the declared Prettier 3.8.1 dependency and passes.
- Browser smoke no longer waits on HMR-sensitive `networkidle`; it uses bounded
  readiness checks and fixture-backed state coverage. The render test and live
  browser smoke both exit 0.

The former opportunity-ranking failure was an incorrect test contract:
active-league opportunities now preserve value-first ordering while retaining
positional need as explanatory context rather than a score multiplier.

## Mutation boundary and artifact note

- All implementation changes remain confined to the protected v2 worktree;
  the primary dirty `dev` checkout has not been staged, reset, stashed,
  committed, folded, pushed, or published. Milestones 1–8 now have implemented
  consumers and verification evidence. The protected branch is now ready for
  the authorized local fold, subject to the post-merge gates.
- An untracked `data/fantasy.duckdb.wal` was present in the initial primary
  status snapshot but absent in the final status check. The audit did not
  intentionally delete or restore it; primary database artifact preservation
  is unresolved and must be checked before any future ingestion or migration.
- No existing dirty work in the primary checkout was staged, reset, stashed,
  committed, folded, pushed, or deleted.
- No external league action, trade, waiver submission, or source mutation was
  performed.
- The copied baseline database manifest is
  `docs/modernization/evidence/baseline-database.manifest.json`; it records
  Alembic revision `024_team_context_by_season`, 43 tables, and the copied
  database SHA-256.
- The final rehearsal evidence is in
  `evidence/final-rehearsal.json`. A fresh Pronto refresh was not required for
  the protected implementation gate; the earlier Ready snapshot remains
  routing context, not new verification evidence.

## Next safe step

Fold the protected branch into canonical `dev` in an isolated worktree and
rerun the repository gates. Keep the legacy revision-024 database and the
preservation refs as rollback boundaries; push only after live remote
verification succeeds, and leave application cutover/deployment separately
gated.
