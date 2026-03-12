from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import polars as pl

SLEEPER_TO_NFLDATA_MAP: dict[str, str] = {
    "rec": "receptions",
    "rec_yd": "receiving_yards",
    "rec_td": "receiving_tds",
    "rush_yd": "rushing_yards",
    "rush_td": "rushing_tds",
    "rush_att": "carries",
    "pass_yd": "passing_yards",
    "pass_td": "passing_tds",
    "pass_int": "interceptions",
    "pass_2pt": "passing_2pt_conversions",
    "bonus_rec_te": "receptions",
    "rec_2pt": "receiving_2pt_conversions",
    "rush_2pt": "rushing_2pt_conversions",
}

PLAYER_STATS_COLUMNS = [
    "player_id",
    "player_name",
    "position",
    "season",
    "week",
    "receptions",
    "targets",
    "receiving_yards",
    "receiving_tds",
    "rushing_yards",
    "rushing_tds",
    "carries",
    "passing_yards",
    "passing_tds",
    "interceptions",
    "passing_2pt_conversions",
    "receiving_2pt_conversions",
    "rushing_2pt_conversions",
    "fantasy_points",
]


def compute_fantasy_points(
    stats_row: dict[str, Any], scoring_settings: dict[str, float], position: str
) -> tuple[float, list[str]]:
    total = 0.0
    unmapped_keys: list[str] = []

    for sleeper_key, points_per_unit in scoring_settings.items():
        nfldata_col = SLEEPER_TO_NFLDATA_MAP.get(sleeper_key)
        if nfldata_col is None:
            unmapped_keys.append(sleeper_key)
            continue

        if sleeper_key == "bonus_rec_te" and position != "TE":
            continue

        stat_value = float(stats_row.get(nfldata_col, 0.0) or 0.0)
        total += stat_value * float(points_per_unit)

    return round(total, 2), unmapped_keys


class NflDataPyLoader:
    def load_weekly_stats(self, years: list[int]) -> pl.DataFrame:
        import nfl_data_py as nfl

        pandas_df = nfl.import_weekly_data(years)
        if pandas_df is None or pandas_df.empty:
            return pl.DataFrame(schema={column: pl.Float64 for column in PLAYER_STATS_COLUMNS})

        df = pl.from_pandas(pandas_df)
        for column in PLAYER_STATS_COLUMNS:
            if column not in df.columns:
                df = df.with_columns(pl.lit(None).alias(column))

        return df.select(PLAYER_STATS_COLUMNS)

    def upsert_weekly_stats(self, conn: duckdb.DuckDBPyConnection, df: pl.DataFrame) -> None:
        if df.height == 0:
            return

        prepared = df.select(PLAYER_STATS_COLUMNS)
        conn.register("weekly_df", prepared)
        conn.execute(
            """
            INSERT INTO player_stats_weekly
            SELECT * FROM weekly_df
            ON CONFLICT (player_id, season, week) DO UPDATE SET
                player_name = EXCLUDED.player_name,
                position = EXCLUDED.position,
                receptions = EXCLUDED.receptions,
                targets = EXCLUDED.targets,
                receiving_yards = EXCLUDED.receiving_yards,
                receiving_tds = EXCLUDED.receiving_tds,
                rushing_yards = EXCLUDED.rushing_yards,
                rushing_tds = EXCLUDED.rushing_tds,
                carries = EXCLUDED.carries,
                passing_yards = EXCLUDED.passing_yards,
                passing_tds = EXCLUDED.passing_tds,
                interceptions = EXCLUDED.interceptions,
                passing_2pt_conversions = EXCLUDED.passing_2pt_conversions,
                receiving_2pt_conversions = EXCLUDED.receiving_2pt_conversions,
                rushing_2pt_conversions = EXCLUDED.rushing_2pt_conversions,
                fantasy_points = EXCLUDED.fantasy_points
            """
        )
        conn.unregister("weekly_df")


def load_adp_baseline(conn: duckdb.DuckDBPyConnection, csv_path: str = "data/adp_baseline.csv") -> int:
    path = Path(csv_path)
    if not path.is_absolute():
        repo_root = Path(__file__).resolve().parents[4]
        path = repo_root / path

    if not path.exists():
        return 0

    df = pl.read_csv(path)
    if df.height == 0:
        return 0

    lower_to_original = {column.lower(): column for column in df.columns}

    player_id_col = lower_to_original.get("player_id") or lower_to_original.get("id")
    player_name_col = (
        lower_to_original.get("player_name")
        or lower_to_original.get("name")
        or lower_to_original.get("player")
    )
    position_col = lower_to_original.get("position") or lower_to_original.get("pos")
    adp_col = lower_to_original.get("adp") or lower_to_original.get("overall")

    if player_name_col is None or adp_col is None:
        raise ValueError("ADP CSV must include player name and ADP columns.")

    rows: list[tuple[Any, Any, Any, Any, str]] = []
    for record in df.to_dicts():
        rows.append(
            (
                record.get(player_id_col) if player_id_col else None,
                record.get(player_name_col),
                record.get(position_col) if position_col else None,
                float(record.get(adp_col)) if record.get(adp_col) not in (None, "") else None,
                "fantasypros_csv",
            )
        )

    conn.execute("DELETE FROM player_adp_baseline")
    conn.executemany(
        """
        INSERT INTO player_adp_baseline (player_id, player_name, position, adp, adp_source)
        VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )
    return len(rows)


__all__ = ["NflDataPyLoader", "SLEEPER_TO_NFLDATA_MAP", "compute_fantasy_points", "load_adp_baseline"]
