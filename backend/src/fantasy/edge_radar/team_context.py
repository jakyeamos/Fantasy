from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import duckdb

TEAM_CONTEXT_DDL = """
    CREATE TABLE IF NOT EXISTS team_context_by_season (
        team                  VARCHAR NOT NULL,
        season                INTEGER NOT NULL,
        head_coach            VARCHAR,
        offensive_coordinator VARCHAR,
        play_caller           VARCHAR,
        offensive_system      VARCHAR,
        pace_label            VARCHAR,
        pass_rate_label       VARCHAR,
        source                VARCHAR NOT NULL DEFAULT 'manual_csv',
        notes                 VARCHAR,
        loaded_at             TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (team, season)
    )
"""

TEAM_CONTEXT_COLUMNS = [
    "season",
    "team",
    "head_coach",
    "offensive_coordinator",
    "play_caller",
    "offensive_system",
    "pace_label",
    "pass_rate_label",
    "source",
    "notes",
]


@dataclass(frozen=True)
class TeamContextImportSummary:
    source_rows: int
    upserted_rows: int


def ensure_team_context_schema(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(TEAM_CONTEXT_DDL)


def import_team_context_csv(
    conn: duckdb.DuckDBPyConnection,
    csv_path: str | Path,
) -> TeamContextImportSummary:
    ensure_team_context_schema(conn)
    rows = _read_team_context_rows(Path(csv_path))
    if rows:
        conn.executemany(
            """
            INSERT INTO team_context_by_season (
                season, team, head_coach, offensive_coordinator, play_caller,
                offensive_system, pace_label, pass_rate_label, source, notes, loaded_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT (team, season) DO UPDATE SET
                head_coach = EXCLUDED.head_coach,
                offensive_coordinator = EXCLUDED.offensive_coordinator,
                play_caller = EXCLUDED.play_caller,
                offensive_system = EXCLUDED.offensive_system,
                pace_label = EXCLUDED.pace_label,
                pass_rate_label = EXCLUDED.pass_rate_label,
                source = EXCLUDED.source,
                notes = EXCLUDED.notes,
                loaded_at = EXCLUDED.loaded_at
            """,
            rows,
        )
    return TeamContextImportSummary(source_rows=len(rows), upserted_rows=len(rows))


def _read_team_context_rows(csv_path: Path) -> list[list[str | int | None]]:
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows: list[list[str | int | None]] = []
        for raw in reader:
            season_raw = (raw.get("season") or "").strip()
            team = (raw.get("team") or "").strip().upper()
            if not season_raw or not team:
                continue
            rows.append(
                [
                    int(season_raw),
                    team,
                    _clean(raw.get("head_coach")),
                    _clean(raw.get("offensive_coordinator")),
                    _clean(raw.get("play_caller")),
                    _clean(raw.get("offensive_system")),
                    _clean(raw.get("pace_label")),
                    _clean(raw.get("pass_rate_label")),
                    _clean(raw.get("source")) or "manual_csv",
                    _clean(raw.get("notes")),
                ]
            )
    return rows


def _clean(value: str | None) -> str | None:
    cleaned = (value or "").strip()
    return cleaned or None


__all__ = [
    "TEAM_CONTEXT_COLUMNS",
    "TEAM_CONTEXT_DDL",
    "TeamContextImportSummary",
    "ensure_team_context_schema",
    "import_team_context_csv",
]
