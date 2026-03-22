# Phase 2 Engineer Handoff

Date: 2026-03-21
Owner: Codex planning-time execution boundary
Scope: `.planning/phases/02-team-intelligence` plans 00-04

## Codex-Owned Execution

Confident to execute directly:
- Plan `02-00`: Alembic migration `004`, `fantasy.intelligence` package skeleton, constants/models, and failing/placeholder test scaffolds.
- Plans `02-01` through `02-03`: deterministic `ScorecardEngine`, `DirectionEngine`, and `ValuationEngine` logic over seeded DuckDB fixtures and synthetic roster scenarios.
- Plan `02-04`: router wiring, persistence of computed outputs, seeded integration tests, and graceful handling when Phase 1 inputs are incomplete but structurally valid.
- Test work that proves importability, migration integrity, response contracts, and deterministic behavior against local fixtures.

## Deferred For Another Engineer

Leave these items to a follow-up engineer or league owner:
- Final calibration of direction weights, age curves, and valuation coefficients against real league data.
- Any validation that depends on a production-quality ADP baseline file or a fresh live Sleeper ingest.
- The manual direction-label sign-off required before downstream phases rely on these outputs for dashboard, profiling, and trade recommendations.
- Any dispute between deterministic engine output and domain judgment on real rosters; Codex should not self-approve those judgment calls.

## Stop Conditions

Codex should stop execution and hand off when:
- Synthetic and seeded tests pass, but confidence now depends on real league review rather than code correctness.
- A plan requires subjective dynasty calibration rather than deterministic implementation.
- Direction labels appear plausible in fixtures but still require league-specific human confirmation.
