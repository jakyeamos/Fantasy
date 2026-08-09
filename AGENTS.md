# AGENTS.md — Fantasy

## Constraints

- **DB:** Local DuckDB (`data/fantasy.duckdb`) — no network DB, no auth required for dev. Never edit schema directly — use Alembic migrations.
- **Grounded fantasy answers:** Before answering roster, player, trade, pick, waiver, lineup, standings, or team-direction questions, query the local database read-only. Do not ask the user for league context already present in the repository. Treat ingested league data as the primary source for ownership and format, report its freshness, and use external market data only as a secondary input. Read `.agents/context/fantasy-decisions.md` for the workflow.
- **Types:** Frontend types in `frontend/src/api/types.ts` — update when API response shape changes.
- **Ingestion:** Sleeper API scripts must be re-run when league data is stale — don't assume data is current.
- `main` must run locally at all times.

## References

- Stack, commands, architecture: `.planning/PROJECT.md`, `.planning/ROADMAP.md`
- Vault: `[[03 Projects/Fantasy]]`
