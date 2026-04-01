Phase 8 supports a pre-draft scoring mode for upcoming rookie classes.

Create a CSV with at least these columns:
- `player_name`
- `position`

You can optionally add a sibling enrichment file named like `2026.enrichment.csv`.
The loader will left-join it onto the base file by `player_name` and `position`, use
enrichment values when the same column exists in both files, and keep base values
for columns the enrichment file does not provide.

Useful optional columns:
- `player_id`
- `expected_draft_ovr`
- `draft_ovr`
- `adp`
- `age_at_draft`
- `forty`
- `weight`
- `height`
- `vertical`
- `bench`
- `cone`
- `shuttle`
- `college_rec_ypg`
- `college_rush_ypg`
- `college_games`
- `college_targets`
- `college_receptions`
- `college_receiving_yards`
- `college_receiving_tds`
- `college_routes_run`
- `college_carries`
- `college_rushing_yards`
- `college_rushing_tds`
- `college_pass_attempts`
- `college_completions`
- `college_passing_yards`
- `college_passing_tds`
- `college_interceptions`
- `college_yprr`
- `college_ypt`
- `college_ypc`
- `college_ypa`
- `college_pass_td_rate`
- `college_qb_rush_yards`
- `college_qb_rush_tds`
- `college_qb_rush_ypg`
- `college_scramble_rate`
- `college_mkt_share_proxy`
- `college_td_rate`
- `college_completion_pct_proxy`

Example:

```csv
player_name,position,expected_draft_ovr,age_at_draft,forty,weight,height,vertical,college_games,college_targets,college_receptions,college_receiving_yards,college_receiving_tds,college_routes_run,college_pass_attempts,college_completions,college_passing_yards,college_passing_tds,college_qb_rush_yards,college_qb_rush_tds,college_scramble_rate,adp
Future QB,QB,4,21,4.55,220,75,35,13,,,,,,430,289,3340,28,455,8,0.12,2
Future WR,WR,18,22,4.41,198,73,39,12,118,74,1098,11,382,,,,,,,9
```

Run it from the repo root:

```bash
cd backend
./.venv/bin/python -m fantasy.prospects.pipeline \
  --db-path ../data/fantasy.duckdb \
  --mode pre_draft \
  --pre-draft-csv ../data/prospects/2026.csv \
  --current-class-year 2026 \
  --positions QB,RB,WR,TE
```

To source-backfill a sibling enrichment file from live StatMuse and PFF pages:

```bash
python3 data/prospects/backfill_enrichment.py \
  --base-csv data/prospects/2026.csv \
  --enrichment-csv data/prospects/2026.enrichment.csv \
  --season 2025
```

Notes:
- `expected_draft_ovr` is used as draft capital when actual NFL picks do not exist yet.
- If `adp` is missing, the pipeline falls back to `expected_draft_ovr` or `draft_ovr`.
- If `player_id` is missing, the pipeline generates a stable `pre_<year>_<name>` identifier.
- The loader will derive model-facing features like `college_rec_ypg`, `college_yprr`, `college_ypa`, `college_pass_td_rate`, and `college_qb_rush_ypg` from the raw stat columns when those direct proxy columns are not provided.
- The enrichment sidecar is the safest place to backfill raw production or combine numbers without rewriting the base ranking board.
- `backfill_enrichment.py` does not generate estimates. It only writes values that were fetched from live sources and leaves unavailable fields blank.
