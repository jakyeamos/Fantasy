---
schemaVersion: 1
healthScore: 78
nextStep: "Populate curated coach/system rows and dense player-role metadata now that Edge Radar can refresh measurable team environment labels from nflreadpy team stats."
blockers:
  - "Schema changes still require Alembic, startup compat shims, and test bootstrap updates in parallel."
  - "New tables still depend on a manual `alembic upgrade head` step because there is no startup migration runner."
lastUpdated: "2026-06-28"
tags:
  - fantasy-football
  - fastapi
  - react
  - duckdb
---

## Summary

Fantasy is a local-first dynasty fantasy football intelligence app with a FastAPI backend, React/Vite frontend, and DuckDB persistence. The planning state shows heavy recent progress, with Phase 21 completed for player-value trends and market-inefficiency trade suggestions and the repo now sitting at a mature but still actively evolving stage.

## Context

The repo layout is backend/frontend/data, and `.planning/STATE.md` records 16 completed phases and 77 completed plans. Current focus is the opportunity-feed and trend-engine work that landed in Phase 21 plus follow-on Edge Radar market-delta and similarity work. Counterparty player selection in trade evaluation is restored as of 2026-06-13; remaining trade scope is multi-team third-party scoring.

## Risks

Schema management is split across Alembic migrations, startup compatibility shims, and test bootstrap code, which is fragile when new tables land. The state file also calls out silent exception swallowing in several backend paths, so invisible failures remain a code-quality risk.

## Recent Documentation Updates

- 2026-05-18: Added or expanded README coverage for project and subproject roots so workspace documentation inventory is complete.
- 2026-06-13: Restored the trade evaluator counterparty asset picker so blank player browsing on "You Receive" scopes to the selected manager roster, with backend integration coverage and frontend roster-target coverage.
- 2026-06-28: Added a curated `team_context_by_season` source path for Edge Radar coach/system similarity, including Alembic schema, runtime/test schema compatibility, CSV import support, source health, and backend regression coverage.
- 2026-06-28: Upgraded Edge Radar similarity to score usage, efficiency, role quality, team environment, career arc, market behavior, and forward outcome comp windows when those fields are present; split dense similarity logic out of the ranking engine.
- 2026-06-28: Added `TeamContextRefreshService` and `POST /ingest/team-context/refresh` to automate measurable team-environment labels from nflreadpy team stats while preserving curated coach/system fields.
