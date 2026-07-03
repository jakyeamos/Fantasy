from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb

from fantasy.config import REPO_ROOT
from fantasy.db.connection import close_connection, get_write_connection

DENSE_PLAYER_METADATA_CSV_PATH = (
    REPO_ROOT / "data" / "edge_radar" / "player_dense_metadata.csv"
)


@dataclass(frozen=True)
class PlayerMetadataRefreshSummary:
    season: int
    source_rows: int
    updated_rows: int


@dataclass(frozen=True)
class PlayerMetadataImportSummary:
    source_rows: int
    matched_rows: int
    updated_rows: int
    unmatched_rows: int


FIELD_ALIASES = {
    "yprr": "yards_per_route_run",
    "yards_per_route_run": "yards_per_route_run",
    "route_participation": "route_participation",
    "snap_share": "snap_share",
    "first_read_share": "first_read_target_share",
    "first_read_target_share": "first_read_target_share",
    "slot_rate": "slot_rate",
    "wide_rate": "wide_rate",
    "alignment": "alignment",
    "yards_after_catch": "yards_after_catch",
    "missed_tackles_forced": "missed_tackles_forced",
    "explosive_play_rate": "explosive_play_rate",
    "goal_line_share": "goal_line_share",
    "two_minute_snap_share": "two_minute_snap_share",
    "third_down_snap_share": "third_down_snap_share",
    "source": "dense_metadata_source",
    "notes": "dense_metadata_notes",
}


def _loads(raw: str | None) -> dict[str, Any]:
    if raw is None:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _dumps(value: dict[str, Any]) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _safe_float(value: object) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def import_player_metadata_csv(
    conn: duckdb.DuckDBPyConnection,
    csv_path: str | Path = DENSE_PLAYER_METADATA_CSV_PATH,
) -> PlayerMetadataImportSummary:
    source_rows = 0
    matched_rows = 0
    updated_rows = 0
    with Path(csv_path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            source_rows += 1
            player_id = _resolve_player_id(conn, raw)
            if not player_id:
                continue
            existing = conn.execute(
                "SELECT metadata_blob FROM players WHERE player_id = ?",
                [player_id],
            ).fetchone()
            if existing is None:
                continue
            matched_rows += 1
            metadata = _loads(str(existing[0]) if existing[0] else None)
            updates = _metadata_updates_from_row(raw)
            if not updates:
                continue
            metadata.update(updates)
            conn.execute(
                """
                UPDATE players
                SET metadata_blob = ?, refreshed_at = CURRENT_TIMESTAMP
                WHERE player_id = ?
                """,
                [_dumps(metadata), player_id],
            )
            updated_rows += 1
    return PlayerMetadataImportSummary(
        source_rows=source_rows,
        matched_rows=matched_rows,
        updated_rows=updated_rows,
        unmatched_rows=source_rows - matched_rows,
    )


def _resolve_player_id(
    conn: duckdb.DuckDBPyConnection,
    raw: dict[str, str],
) -> str:
    player_id = str(raw.get("player_id") or "").strip()
    if player_id:
        exists = conn.execute(
            "SELECT 1 FROM players WHERE player_id = ?",
            [player_id],
        ).fetchone()
        if exists is not None:
            return player_id

    player_name = str(raw.get("player_name") or raw.get("full_name") or "").strip()
    if not player_name:
        return ""
    matches = conn.execute(
        """
        SELECT player_id
        FROM players
        WHERE lower(full_name) = lower(?)
        ORDER BY player_id
        LIMIT 2
        """,
        [player_name],
    ).fetchall()
    if len(matches) != 1:
        return ""
    return str(matches[0][0])


def import_curated_dense_player_metadata(
    conn: duckdb.DuckDBPyConnection,
) -> PlayerMetadataImportSummary:
    return import_player_metadata_csv(conn, DENSE_PLAYER_METADATA_CSV_PATH)


def _metadata_updates_from_row(raw: dict[str, str]) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    for raw_key, value in raw.items():
        key = FIELD_ALIASES.get(raw_key.strip())
        if key is None or value in (None, ""):
            continue
        cleaned = value.strip()
        if not cleaned:
            continue
        updates[key] = _typed_value(cleaned)
    return updates


def _typed_value(value: str) -> str | float:
    try:
        return float(value)
    except ValueError:
        return value


class PlayerMetadataRefreshService:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def refresh(self, season: int) -> PlayerMetadataRefreshSummary:
        rows = self._player_rows(season)
        team_totals = self._team_totals(rows)
        previous_usage = self._previous_usage(season)
        market_movement = self._market_movement()
        updated = 0
        for row in rows:
            metadata = _loads(str(row["metadata_blob"]) if row["metadata_blob"] else None)
            team = str(row["team"] or "")
            target_total = team_totals.get(team, {}).get("targets", 0.0)
            carry_total = team_totals.get(team, {}).get("carries", 0.0)
            targets = _safe_float(row["targets"])
            carries = _safe_float(row["carries"])
            games = max(1.0, _safe_float(row["games"]))
            current_usage = (targets + carries) / games
            prior_usage = previous_usage.get(str(row["player_id"]), 0.0)
            derived = {
                "weekly_targets": round(targets / games, 2),
                "weekly_carries": round(carries / games, 2),
                "target_share": round(targets / target_total, 2) if target_total > 0 else 0.0,
                "carry_share": round(carries / carry_total, 2) if carry_total > 0 else 0.0,
                "yoy_role_growth": (
                    round((current_usage - prior_usage) / prior_usage, 2)
                    if prior_usage > 0
                    else 0.0
                ),
            }
            if str(row["player_id"]) in market_movement:
                derived["trade_value_movement"] = market_movement[str(row["player_id"])]
            metadata.update(derived)
            self._conn.execute(
                """
                UPDATE players
                SET metadata_blob = ?, refreshed_at = CURRENT_TIMESTAMP
                WHERE player_id = ?
                """,
                [_dumps(metadata), row["player_id"]],
            )
            updated += 1
        return PlayerMetadataRefreshSummary(
            season=season,
            source_rows=len(rows),
            updated_rows=updated,
        )

    def _player_rows(self, season: int) -> list[dict[str, object]]:
        rows = self._conn.execute(
            """
            SELECT p.player_id,
                   p.team,
                   p.metadata_blob,
                   COUNT(ps.week) AS games,
                   COALESCE(SUM(ps.targets), 0.0) AS targets,
                   COALESCE(SUM(ps.carries), 0.0) AS carries
            FROM players p
            JOIN player_stats_weekly ps ON ps.player_id = p.player_id
            WHERE ps.season = ?
            GROUP BY p.player_id, p.team, p.metadata_blob
            """,
            [season],
        ).fetchall()
        keys = ("player_id", "team", "metadata_blob", "games", "targets", "carries")
        return [dict(zip(keys, row, strict=True)) for row in rows]

    def _team_totals(
        self,
        rows: list[dict[str, object]],
    ) -> dict[str, dict[str, float]]:
        totals: dict[str, dict[str, float]] = {}
        for row in rows:
            team = str(row["team"] or "")
            if not team:
                continue
            totals.setdefault(team, {"targets": 0.0, "carries": 0.0})
            totals[team]["targets"] += _safe_float(row["targets"])
            totals[team]["carries"] += _safe_float(row["carries"])
        return totals

    def _previous_usage(self, season: int) -> dict[str, float]:
        rows = self._conn.execute(
            """
            SELECT player_id,
                   COUNT(week) AS games,
                   COALESCE(SUM(targets), 0.0) + COALESCE(SUM(carries), 0.0) AS usage
            FROM player_stats_weekly
            WHERE season = ?
            GROUP BY player_id
            """,
            [season - 1],
        ).fetchall()
        usage: dict[str, float] = {}
        for player_id, games, total_usage in rows:
            game_count = max(1.0, _safe_float(games))
            usage[str(player_id)] = _safe_float(total_usage) / game_count
        return usage

    def _market_movement(self) -> dict[str, float]:
        rows = self._conn.execute(
            """
            SELECT player_id, fantasycalc_value, fantasycalc_trend30
            FROM market_values
            WHERE fantasycalc_value IS NOT NULL
              AND fantasycalc_value != 0
              AND fantasycalc_trend30 IS NOT NULL
            """
        ).fetchall()
        return {
            str(player_id): round(float(trend) / float(value), 2)
            for player_id, value, trend in rows
        }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Import curated dense Edge Radar player metadata into DuckDB."
    )
    parser.add_argument(
        "--csv-path",
        type=Path,
        default=DENSE_PLAYER_METADATA_CSV_PATH,
        help=f"CSV path to import. Defaults to {DENSE_PLAYER_METADATA_CSV_PATH}.",
    )
    args = parser.parse_args(argv)

    conn = get_write_connection()
    try:
        summary = import_player_metadata_csv(conn, args.csv_path)
    finally:
        close_connection(conn)

    print(
        "Imported dense player metadata: "
        f"{summary.updated_rows}/{summary.source_rows} rows updated "
        f"({summary.unmatched_rows} unmatched)."
    )
    return 0


__all__ = [
    "DENSE_PLAYER_METADATA_CSV_PATH",
    "PlayerMetadataImportSummary",
    "PlayerMetadataRefreshService",
    "PlayerMetadataRefreshSummary",
    "import_curated_dense_player_metadata",
    "import_player_metadata_csv",
]


if __name__ == "__main__":
    raise SystemExit(main())
