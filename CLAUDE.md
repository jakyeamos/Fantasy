# CLAUDE.md — Fantasy

## Constraints

- **DB:** Local DuckDB (`data/fantasy.duckdb`) — no network DB, no auth required for dev. Never edit schema directly — use Alembic migrations.
- **Types:** Frontend types in `frontend/src/api/types.ts` — update when API response shape changes.
- **Ingestion:** Sleeper API scripts must be re-run when league data is stale — don't assume data is current.
- `main` must run locally at all times.

## References

- Stack, commands, architecture: `.planning/PROJECT.md`, `.planning/ROADMAP.md`
- Vault: `[[03 Projects/Fantasy]]`
