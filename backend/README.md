# Fantasy backend

## Future Pick Inventory

The pick API and agent context expose a rolling three-draft inventory. Once the
current season's rookie draft has been completely ingested, that completed year
is excluded and the next draft year enters the window. Residual historical rows
from Sleeper's traded-picks feed do not make completed picks tradable again.

Future picks are valued from the original owner's current `team_scorecards.win_now`
rank when every league roster has a scorecard. The projection regresses toward
the league midpoint for more distant years and applies the configured annual
future-value discount. If complete scorecard evidence is unavailable, the engine
falls back to the league's configured standings or max-points-for draft-order
rule. API and agent-context values include `projection_source` and
`original_owner_strength_slot` so the basis is machine-readable.

## Dev Auto-Refresh

When you are iterating on backend logic and want the local league data rebuilt on
every FastAPI reload, start the backend with `FANTASY_DEV_AUTO_REFRESH=1`.

Example:

```bash
cd backend
FANTASY_DEV_AUTO_REFRESH=1 \
FANTASY_DEV_AUTO_REFRESH_INGEST_MODE=incremental \
.venv/bin/uvicorn fantasy.main:app --reload
```

Behavior:

- If `FANTASY_DEV_AUTO_REFRESH_LEAGUES` is empty, the startup hook refreshes every
  league already present in the local DuckDB file.
- Set `FANTASY_DEV_AUTO_REFRESH_LEAGUES` to a comma-separated list when you want
  to force a specific league on a fresh DB.
- `FANTASY_DEV_AUTO_REFRESH_INGEST_MODE` accepts `incremental`, `full`, or
  `skip`.
- After ingest, the backend also recomputes intelligence, manager profiles, and
  snapshots so the UI is reading rebuilt artifacts instead of stale cached data.

## Personalizing The Dashboard

Set one of these environment variables when you want the dashboard to use your
roster perspective instead of guessing:

- `FANTASY_PORTFOLIO_OWNER_DISPLAY_NAME`
- `FANTASY_PORTFOLIO_OWNER_ID`

Example:

```bash
FANTASY_PORTFOLIO_OWNER_DISPLAY_NAME=jakye \
.venv/bin/uvicorn fantasy.main:app --reload
```

The backend also reads a repo-root `.env`, so local personalization can live
there instead of being repeated in every shell session.

## ADP Baseline Refresh (API)

To refresh `player_adp_baseline` without a CSV export, call:

```bash
curl -X POST "http://127.0.0.1:8000/ingest/adp-baseline/refresh?league_id=<league_id>"
```

Notes:

- This pulls dynasty values from FantasyCalc and maps them to local Sleeper
  player IDs.
- League profile defaults are inferred from `leagues`/`rosters` (1QB vs SF,
  team count, and PPR). You can override with query params:
  `num_qbs`, `num_teams`, `ppr`.
- The refresh is safety-guarded: if zero players match local IDs, the existing
  ADP baseline is left unchanged.

## Dense Player Metadata CSV

Edge Radar reads curated route/usage fields from
`data/edge_radar/player_dense_metadata.csv` by default. The committed file is
header-only until real sourced metrics are curated. Import the repo-owned CSV
into local DuckDB with:

```bash
cd backend
uv run python -m fantasy.edge_radar.player_metadata
```

or through the API:

```bash
curl -X POST "http://127.0.0.1:8000/ingest/player-metadata/import-csv"
```

Use `csv_path` when importing a different export:

```bash
curl -X POST "http://127.0.0.1:8000/ingest/player-metadata/import-csv?csv_path=/absolute/path/to/player_dense_metadata.csv"
```
# Fantasy-agent verification

Run backend tests, frontend quality gates, migration-head validation, diff
validation, and live capability checks through one machine-readable boundary:

```bash
uv run fantasy-agent-check --json
```

The report preserves `passed`, `degraded`, `unavailable`, and `failed` states.
