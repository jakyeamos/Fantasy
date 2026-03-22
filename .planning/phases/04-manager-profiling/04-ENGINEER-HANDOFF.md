# Phase 4 Engineer Handoff

Date: 2026-03-21
Owner: Codex planning-time execution boundary
Scope: `.planning/phases/04-manager-profiling` plans 01-04

## Codex-Owned Execution

Confident to execute directly:
- Plan `04-01`: profiling constants, Pydantic models, migration `006`, and DuckDB repository layer.
- Plan `04-02`: deterministic profiling engine, FastAPI router, and tests against seeded trade-history fixtures.
- Plans `04-03` and `04-04`: managers list, dossier routes, and tabbed UI using the existing Phase 3 frontend patterns and UI spec.
- LOW-confidence labeling mechanics, evidence-count display rules, and pitch-angle rendering based on stored profile outputs.

## Deferred For Another Engineer

Leave these items to a follow-up engineer or domain reviewer:
- Final calibration of exploitability scoring weights, secondary-type thresholds, and ADP-based value-delta interpretation on real trades.
- Sanity review of pitch-angle usefulness on real leaguemates; Codex can generate templates but should not self-certify their strategic sharpness.
- Any refinement required because real transaction history is sparse, noisy, or league-specific in ways not captured by seeded fixtures.
- Execution before the Phase 3 direction-label gate is cleared.

## Stop Conditions

Codex should stop execution and hand off when:
- The remaining work is threshold tuning or judgment-heavy strategy review rather than deterministic implementation.
- Dossier outputs are technically correct but need a dynasty player to decide whether the classification is strategically credible.
- Real-league evidence is too thin to justify stronger claims than the existing LOW-confidence behavior.
