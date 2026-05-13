from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import duckdb
import polars as pl

from fantasy.market.fantasycalc_client import FantasyCalcClient

if TYPE_CHECKING:
    from fantasy.market.models import ExternalPlayerValue

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

_SUFFIX_TOKENS = {"jr", "sr", "ii", "iii", "iv", "v"}


def _normalize_player_name(name: str) -> str:
    cleaned = re.sub(r"[^a-z0-9 ]+", " ", str(name).lower())
    tokens = [token for token in cleaned.split() if token]
    while tokens and tokens[-1] in _SUFFIX_TOKENS:
        tokens.pop()
    return " ".join(tokens)


def _players_has_mfl_column(conn: duckdb.DuckDBPyConnection) -> bool:
    columns = conn.execute("PRAGMA table_info('players')").fetchall()
    return any(str(column[1]) == "mfl_id" for column in columns)


def _build_player_lookup(
    conn: duckdb.DuckDBPyConnection,
) -> tuple[dict[str, str], dict[str, list[tuple[str, str | None, str]]]]:
    if _players_has_mfl_column(conn):
        rows = conn.execute(
            """
            SELECT player_id, full_name, position, mfl_id
            FROM players
            """
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT player_id, full_name, position, NULL AS mfl_id
            FROM players
            """
        ).fetchall()

    by_mfl: dict[str, str] = {}
    by_name: dict[str, list[tuple[str, str | None, str]]] = {}
    for row in rows:
        player_id = str(row[0])
        full_name = str(row[1] or "")
        position = str(row[2]) if row[2] is not None else None
        mfl_id = str(row[3]) if row[3] is not None else None

        if mfl_id:
            by_mfl[mfl_id] = player_id
        if full_name:
            normalized = _normalize_player_name(full_name)
            if normalized:
                by_name.setdefault(normalized, []).append((player_id, position, full_name))
    return by_mfl, by_name


def _resolve_player_id(
    value: "ExternalPlayerValue",
    by_mfl: dict[str, str],
    by_name: dict[str, list[tuple[str, str | None, str]]],
) -> tuple[str | None, str | None]:
    if value.mfl_id is not None:
        resolved = by_mfl.get(str(value.mfl_id))
        if resolved is not None:
            return resolved, None

    normalized_name = _normalize_player_name(value.player_name)
    candidates = by_name.get(normalized_name, [])
    if not candidates:
        return None, None
    if len(candidates) == 1:
        player_id, _position, canonical_name = candidates[0]
        return player_id, canonical_name

    if value.position:
        matching_position = [
            candidate
            for candidate in candidates
            if candidate[1] is not None and candidate[1] == value.position
        ]
        if len(matching_position) == 1:
            player_id, _position, canonical_name = matching_position[0]
            return player_id, canonical_name

    return None, None


async def refresh_adp_baseline_from_fantasycalc(
    conn: duckdb.DuckDBPyConnection,
    *,
    num_qbs: int = 1,
    num_teams: int = 12,
    ppr: float = 1.0,
) -> dict[str, int]:
    if num_qbs <= 0:
        raise ValueError("num_qbs must be positive.")
    if num_teams <= 0:
        raise ValueError("num_teams must be positive.")

    by_mfl, by_name = _build_player_lookup(conn)
    async with FantasyCalcClient() as client:
        values = await client.fetch_dynasty_values(
            num_qbs=num_qbs,
            num_teams=num_teams,
            ppr=ppr,
        )

    matched_unique: dict[str, tuple[str, str | None, float, str | None]] = {}
    matched_rows = 0
    for value in values:
        player_id, canonical_name = _resolve_player_id(value, by_mfl=by_mfl, by_name=by_name)
        if player_id is None:
            continue

        matched_rows += 1
        adp_rank = float(value.overall_rank)
        existing = matched_unique.get(player_id)
        if existing is None or adp_rank < existing[2]:
            matched_unique[player_id] = (
                value.player_name,
                value.position,
                adp_rank,
                canonical_name,
            )

    matched_unique_rows = len(matched_unique)
    if matched_unique_rows == 0:
        raise ValueError(
            "FantasyCalc ADP refresh matched zero players in local Sleeper IDs; baseline unchanged."
        )

    rows: list[tuple[str, str | None, str | None, float, str]] = []
    for player_id, (player_name, position, adp_rank, canonical_name) in matched_unique.items():
        rows.append(
            (
                player_id,
                canonical_name or player_name,
                position,
                adp_rank,
                "fantasycalc_api",
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

    if _players_has_mfl_column(conn):
        mfl_updates: list[tuple[str, str]] = []
        for value in values:
            if value.mfl_id is None:
                continue
            player_id, _canonical_name = _resolve_player_id(value, by_mfl=by_mfl, by_name=by_name)
            if player_id is None:
                continue
            mfl_updates.append((str(value.mfl_id), player_id))
        if mfl_updates:
            conn.executemany(
                """
                UPDATE players
                SET mfl_id = ?
                WHERE player_id = ?
                """,
                mfl_updates,
            )

    return {
        "source_rows": len(values),
        "matched_rows": matched_rows,
        "matched_unique_rows": matched_unique_rows,
        "unmatched_rows": len(values) - matched_rows,
    }


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
