# Phase 3 Engineer Handoff

Date: 2026-03-21
Owner: Codex planning-time execution boundary
Scope: `.planning/phases/03-core-dashboard` plans 01-03

## Codex-Owned Execution

Confident to execute directly:
- Plan `03-01`: backend snapshot migration, snapshot service, dashboard/snapshot routers, and post-ingest hook wiring.
- Plan `03-02`: frontend scaffold, route shells, query client wiring, API query definitions, and typed route structure that follows the UI spec.
- Plan `03-03`: dashboard components, loading/error/empty states, and snapshot controls using the documented API contracts.
- Graceful-degradation behavior when Phase 2 tables are empty or absent.

## Deferred For Another Engineer

Leave these items to a follow-up engineer or operator:
- Dependency/bootstrap issues caused by external package drift in npm, shadcn CLI, or frontend tooling.
- Real-browser validation across screen sizes and the final visual pass on interaction quality.
- Validation of snapshot delta semantics against real ingest history and real connected leagues.
- The Phase 3 hard gate: manual review and confirmation that direction labels are materially correct before Phases 4 and 5 proceed.

## Stop Conditions

Codex should stop execution and hand off when:
- The remaining work is live browser QA, device testing, or subjective UI refinement rather than deterministic code implementation.
- Dashboard correctness depends on Phase 2 labels being reviewed by a human on real leagues.
- Snapshot behavior is structurally implemented, but operational trust now depends on repeated real ingest runs.
