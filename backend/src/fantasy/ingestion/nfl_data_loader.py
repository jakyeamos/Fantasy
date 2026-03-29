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
        url = "https://github.com/nflverse/nflverse-data/releases/download/player_stats/player_stats.parquet"
        try:
            df = pl.read_parquet(url)
            df = df.filter(pl.col("season").is_in(years))
            for column in PLAYER_STATS_COLUMNS:
                if column not in df.columns:
                    df = df.with_columns(pl.lit(None).alias(column))
            return df.select(PLAYER_STATS_COLUMNS)
        except Exception:
            return pl.DataFrame(schema={column: pl.Float64 for column in PLAYER_STATS_COLUMNS})

    def upsert_weekly_stats(self, conn: duckdb.DuckDBPyConnection, df: pl.DataFrame) -> None:
        if df.height == 0:
            return

        prepared = df.select(PLAYER_STATS_COLUMNS)

        upsert_sql = """
            INSERT INTO player_stats_weekly
            ({cols})
            VALUES ({placeholders})
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
        """.format(
            cols=", ".join(PLAYER_STATS_COLUMNS),
            placeholders=", ".join(["?"] * len(PLAYER_STATS_COLUMNS)),
        )

        try:
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
        except Exception:
            rows = [
                [row.get(col) for col in PLAYER_STATS_COLUMNS]
                for row in prepared.to_dicts()
            ]
            conn.executemany(upsert_sql, rows)


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

    if player_id_col is None:
        raise ValueError(
            "ADP CSV must include a Sleeper player ID column ('player_id' or 'id')."
        )
    if player_name_col is None or adp_col is None:
        raise ValueError("ADP CSV must include player name and ADP columns.")

    rows: list[tuple[Any, Any, Any, Any, str]] = []
    for index, record in enumerate(df.to_dicts(), start=1):
        player_id = record.get(player_id_col)
        if player_id in (None, ""):
            raise ValueError(
                f"ADP CSV row {index} is missing a Sleeper player ID."
            )
        rows.append(
            (
                str(player_id),
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


# Maps Sleeper stat keys to player_stats_weekly column names (excludes bonus_rec_te duplicate)
_SLEEPER_STAT_TO_COL: dict[str, str] = {
    "rec": "receptions",
    "tgt": "targets",
    "rec_yd": "receiving_yards",
    "rec_td": "receiving_tds",
    "rush_yd": "rushing_yards",
    "rush_td": "rushing_tds",
    "rush_att": "carries",
    "pass_yd": "passing_yards",
    "pass_td": "passing_tds",
    "pass_int": "interceptions",
    "pass_2pt": "passing_2pt_conversions",
    "rec_2pt": "receiving_2pt_conversions",
    "rush_2pt": "rushing_2pt_conversions",
}


def build_sleeper_stats_df(
    all_weeks_stats: "dict[int, dict[str, dict]]",
    scoring_settings: "dict[str, float]",
    season: int,
    player_info: "dict[str, tuple[str, str]]",
) -> "pl.DataFrame":
    """Build a player_stats_weekly DataFrame from Sleeper weekly stats.

    Args:
        all_weeks_stats: week -> {sleeper_player_id -> {stat_key: value}}
        scoring_settings: league scoring config (Sleeper key -> points_per_unit)
        season: NFL season year
        player_info: sleeper_player_id -> (full_name, position)
    """
    rows = []
    for week, week_stats in all_weeks_stats.items():
        for player_id, stats in week_stats.items():
            if not stats:
                continue
            name, position = player_info.get(str(player_id), ("", ""))
            fantasy_pts = 0.0
            for key, pts_per_unit in scoring_settings.items():
                if key == "bonus_rec_te" and position != "TE":
                    continue
                fantasy_pts += float(stats.get(key, 0.0) or 0.0) * float(pts_per_unit)
            row: dict = {
                "player_id": str(player_id),
                "player_name": name or None,
                "position": position or None,
                "season": season,
                "week": week,
                "fantasy_points": round(fantasy_pts, 2),
            }
            for stat_key, col in _SLEEPER_STAT_TO_COL.items():
                if col not in row:
                    row[col] = float(stats.get(stat_key, 0.0) or 0.0)
            for col in PLAYER_STATS_COLUMNS:
                if col not in row:
                    row[col] = None
            rows.append(row)
    if not rows:
        return pl.DataFrame(schema={col: pl.Float64 for col in PLAYER_STATS_COLUMNS})
    return pl.DataFrame(rows).select(PLAYER_STATS_COLUMNS)


__all__ = [
    "NflDataPyLoader",
    "SLEEPER_TO_NFLDATA_MAP",
    "compute_fantasy_points",
    "load_adp_baseline",
    "build_sleeper_stats_df",
]
