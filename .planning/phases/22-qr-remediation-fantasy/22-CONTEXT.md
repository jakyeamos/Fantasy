# Phase 22: QR remediation: fantasy - Context

**Gathered:** 2026-07-04
**Status:** Ready for planning
**Source:** PRD Express Path (/Users/jakyeamos/.local/state/quality-runner/fleet/per-repo-summaries-20260704/fantasy.md)

<domain>
## Phase Boundary

Plan the remediation work for fantasy from Quality Runner run qr-fleet-continue-20260704-fantasy.
This phase is planning-only until execute-phase runs. Quality Runner remains advisory-only: it identifies findings, remediation clusters, and verification suggestions, but all source changes happen in /Users/jakyeamos/projects/Fantasy.

Findings: 20
Severity: `observation` 9, `warning` 11
Categories: `structural:clarify` 1, `structural:deduplicate` 1, `structural:harden` 2, `structural:ponytail` 4, `structural:simplify` 4, `structural:speed` 1, `structural:ui_structural` 7
Fleet phase candidate: Phase 5 - Large Structural Apps
Requirement: QR-FANTASY

</domain>

<decisions>
## Implementation Decisions

### D-01 - QR summary is the planning source
- Use /Users/jakyeamos/.local/state/quality-runner/fleet/per-repo-summaries-20260704/fantasy.md and the artifacts under /Users/jakyeamos/projects/Fantasy/.quality-runner/runs/qr-fleet-continue-20260704-fantasy as the source of truth for this remediation phase.

### D-02 - Cluster-oriented remediation
- Plan and execute coherent remediation batches by QR cluster, not one isolated edit per finding row.

### D-03 - Behavior preservation
- Prefer behavior-preserving refactors, hardening, and simplification. Do not change product behavior unless a QR hardening cluster explicitly requires safer behavior.

### D-04 - Existing project conventions first
- Read the target files and local manifests before editing. Follow existing package-manager, formatter, test, and architecture conventions. Use pnpm for JavaScript package scripts.

### D-05 - Evidence-backed closure
- A cluster is done only when focused repo verification passes and a post-remediation QR run shows the fingerprints cleared or are dispositioned with evidence.

### Claude's Discretion
- Choose exact helper extraction boundaries, naming, and task order when the QR document identifies the finding but not the implementation shape.
- If a cluster turns out to require product, API, or design decisions, stop that cluster and capture the question instead of guessing.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Quality Runner Inputs
- `/Users/jakyeamos/.local/state/quality-runner/fleet/per-repo-summaries-20260704/fantasy.md` - Per-repo QR summary used as this phase PRD.
- `/Users/jakyeamos/projects/Fantasy/.quality-runner/runs/qr-fleet-continue-20260704-fantasy/quality-audit.json` - Quality audit report.
- `/Users/jakyeamos/projects/Fantasy/.quality-runner/runs/qr-fleet-continue-20260704-fantasy/remediation-plan.json` - QR remediation plan.
- `/Users/jakyeamos/projects/Fantasy/.quality-runner/runs/qr-fleet-continue-20260704-fantasy/code-quality-scan.json` - Code-quality scan fingerprints.
- `/Users/jakyeamos/projects/Fantasy/.quality-runner/runs/qr-fleet-continue-20260704-fantasy/resolution-ledger.md` - Resolution ledger for closure evidence.
- `/Users/jakyeamos/projects/Fantasy/.quality-runner/runs/qr-fleet-continue-20260704-fantasy/agent-handoff.md` - QR agent handoff.

</canonical_refs>

<specifics>
## Top Findings

- `structural-simplify-large-source-file` warning structural:simplify: 20 large-source-file structural findings in simplification and shrink pass. Fix: 20 findings, aggregate score 180: Split mixed responsibilities into focused modules. Evidence: backend/src/fantasy/actions/command_center.py:1: large-source-file; backend/src/fantasy/actions/trade_suggestions.py:1: large-source-file; backend/src/fantasy/edge_radar/engine.py:1: large-source-file
- `structural-simplify-deep-nesting` warning structural:simplify: 27 deep-nesting structural findings in simplification and shrink pass. Fix: 27 findings, aggregate score 162: Flatten guard clauses, extract decision helpers, or split rendering branches. Evidence: frontend/scripts/browserSmoke.mjs:26: deep-nesting; frontend/scripts/browserSmoke.mjs:29: deep-nesting; frontend/src/api/queries.ts:312: deep-nesting
- `structural-simplify-nested-ternary` warning structural:simplify: 10 nested-ternary structural findings in simplification and shrink pass. Fix: 10 findings, aggregate score 90: Replace nested ternaries with named branches or helpers. Evidence: frontend/scripts/browserSmoke.mjs:53: nested-ternary; frontend/src/api/queries.ts:107: nested-ternary; frontend/src/api/queries.ts:129: nested-ternary
- `structural-ui_structural-missing-empty-state` warning structural:ui_structural: 13 missing-empty-state structural findings in UI state coverage. Fix: 13 findings, aggregate score 78: Render a deliberate empty state before mapping collection data. Evidence: frontend/src/components/AnchorSelector.tsx:53: missing-empty-state; frontend/src/components/ConcentrationAlertBanner.tsx:58: missing-empty-state; frontend/src/components/SnapshotDiffView.tsx:70: missing-empty-state
- `structural-deduplicate-near-duplicate-function` warning structural:deduplicate: 3 near-duplicate-function structural findings in duplicate consolidation and helper extraction. Fix: 3 findings, aggregate score 18: Extract a shared helper only when the call sites share domain semantics. Evidence: frontend/src/components/LeagueCard.tsx:10: near-duplicate-function; frontend/src/components/actions/CommandCenter.tsx:36: near-duplicate-function; frontend/src/components/picks/LeaguePickList.tsx:23: near-duplicate-function
- `structural-harden-api-route-missing-boundary-validation` warning structural:harden: 3 api-route-missing-boundary-validation structural findings in API hardening and boundary validation. Fix: 3 findings, aggregate score 18: Validate external input at the route or procedure boundary. Evidence: frontend/src/routes/draft-room.tsx:55: api-route-missing-boundary-validation; frontend/src/routes/league.$leagueId.player-rankings.tsx:148: api-route-missing-boundary-validation; frontend/src/routes/opportunities.tsx:192: api-route-missing-boundary-validation
- `structural-simplify-fat-router` warning structural:simplify: 2 fat-router structural findings in simplification and shrink pass. Fix: 2 findings, aggregate score 18: Keep routers focused on validation, authorization, delegation, and response shaping. Evidence: backend/src/fantasy/routers/dashboard.py:1: fat-router; backend/src/fantasy/routers/draft_grades.py:1: fat-router
- `structural-speed-await-in-loop` warning structural:speed: 2 await-in-loop structural findings in performance and batching improvements. Fix: 2 findings, aggregate score 12: Batch independent work or document required sequencing. Evidence: frontend/scripts/browserSmoke.mjs:23: await-in-loop; frontend/scripts/browserSmoke.mjs:115: await-in-loop

## Remediation Clusters

1. remediate-structural-frontend-src-api-queries-ts (medium, score 68) - Remediate structural cluster in frontend/src/api/queries.ts
2. remediate-structural-frontend-scripts-browsersmoke-mjs (medium, score 43) - Remediate structural cluster in frontend/scripts/browserSmoke.mjs
3. remediate-structural-frontend-src-routes-root-tsx (medium, score 42) - Remediate structural cluster in frontend/src/routes/__root.tsx
4. remediate-structural-frontend-src-routes-trades-tsx (medium, score 39) - Remediate structural cluster in frontend/src/routes/trades.tsx
5. remediate-structural-frontend-src-components-snapshotdiffview-tsx (medium, score 24) - Remediate structural cluster in frontend/src/components/SnapshotDiffView.tsx
6. remediate-structural-frontend-src-lib-usetradeprefill-ts (medium, score 24) - Remediate structural cluster in frontend/src/lib/useTradePrefill.ts

</specifics>

<deferred>
## Deferred Ideas

- Broad rewrites outside the QR clusters.
- Running Quality Runner as an executor or letting QR mutate source code.
- Remediating repos outside fantasy; each repo gets its own GSD phase.

</deferred>

---

*Phase: 22*
*Context gathered: 2026-07-04 via QR per-repo PRD*
