# UI Rubric Audit - 2026-06-26

## Scope

Rendered UI audit of the local Fantasy dashboard using the available expert UI rubric workflow. TMCP was not installed or discoverable in this Codex session, so the audit used the in-app Browser workflow with desktop and mobile verification.

## Environment

- App URL: `http://127.0.0.1:5173/`
- Backend URL: `http://127.0.0.1:8000/`
- Desktop viewport: default in-app Browser viewport
- Mobile viewport: `390x844`
- Branch: `codex/snapshot-refresh-fix`

## Rubric Findings

### Fixed: False mobile empty state

Mobile reload at `390x844` initially rendered `No leagues connected. Add a league ID to get started.` while the same backend data showed two tracked leagues on desktop.

Root cause was not mobile layout code. The app was sharing one file-backed DuckDB connection across FastAPI request threads. Concurrent dashboard and opportunity requests could corrupt pending query state, causing later dashboard reads to fail or return the wrong client state.

Resolution:

- `backend/src/fantasy/db/connection.py` now opens request-scoped DuckDB connections.
- File-backed read connections use `read_only=True`.
- `close_connection` closes every request-scoped handle.
- `backend/tests/test_db_connection.py` now asserts independent handles and close behavior.

Verification:

- Desktop dashboard reload rendered two leagues.
- Mobile dashboard reload rendered the same two-league content instead of the empty state.
- Mobile hamburger menu opened and exposed Dashboard, Managers, Portfolio, Trade Lab, and Rookie Board.
- Browser console had no warnings or errors during verified dashboard flows.

### Remaining: Opportunity Feed hangs in skeleton state

The Opportunity Feed route navigates successfully and no longer throws connection-state exceptions, but `/opportunities` can hang past 10 seconds. The UI remains in skeleton loading while the backend request is still running.

Likely area:

- `backend/src/fantasy/trends/opportunity_engine.py`
- `backend/src/fantasy/trends/similarity.py`
- Candidate iteration plus per-player similarity lookups appear unbounded for the current data shape.

Recommended follow-up:

- Add a bounded performance pass for `OpportunityEngine.build_feed`.
- Avoid repeated `list_candidate_players` and `current_snapshot` calls inside similarity loops.
- Add a route-level regression test or benchmark fixture that proves `/opportunities` returns within an acceptable local-dev budget.
- Add an explicit empty, timeout, or degraded state if opportunity computation cannot finish promptly.

## Checks Run

- `pnpm build`
- `uv run pytest tests/test_db_connection.py tests/test_opportunities_router.py tests/test_dashboard_router.py`
- Browser desktop dashboard load
- Browser desktop Portfolio navigation
- Browser desktop Opportunity Feed navigation
- Browser mobile dashboard load at `390x844`
- Browser mobile navigation menu interaction

## Result

The dashboard and mobile navigation passed the rendered UI audit after the DuckDB request connection fix. The Opportunity Feed remains a separate backend performance/product-state issue and should be handled in a dedicated pass.
