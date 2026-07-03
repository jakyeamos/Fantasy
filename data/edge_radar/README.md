# Edge Radar curated data

`player_dense_metadata.csv` is the default local import source for dense player
role metrics that are not available from Sleeper or weekly box-score loaders.
It is intentionally committed with only a header until real sourced values are
curated. Do not add example or estimated rows here; Edge Radar source health
should stay missing until this file contains validated metrics.

Import it with either:

```bash
cd backend
uv run python -m fantasy.edge_radar.player_metadata
```

or while the API is running:

```bash
curl -X POST "http://127.0.0.1:8000/ingest/player-metadata/import-csv"
```

Expected columns:

- `player_id`: Sleeper player ID. If omitted or not matched, the importer uses
  `player_name` only when it uniquely matches `players.full_name`.
- `player_name`
- `yprr` or `yards_per_route_run`
- `route_participation`
- `snap_share`
- `first_read_share` or `first_read_target_share`
- optional `slot_rate`, `wide_rate`, and other dense fields supported by
  `FIELD_ALIASES` in `backend/src/fantasy/edge_radar/player_metadata.py`
- `source`
- `notes`

Edge Radar reports `player_dense_metadata` as ready after at least one imported
player has YPRR, route participation, snap share, and first-read share. If the
file is header-only, importing it should update zero rows and leave that source
missing unless dense metadata already exists in the local database from another
validated import.
