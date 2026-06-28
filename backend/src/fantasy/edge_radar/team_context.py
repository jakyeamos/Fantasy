from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Mapping

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


@dataclass(frozen=True)
class TeamContextRefreshSummary:
    season: int
    environment_rows: int
    upserted_rows: int


TeamStatsLoader = Callable[[int], Iterable[Mapping[str, object]]]


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


class TeamContextRefreshService:
    def __init__(
        self,
        conn: duckdb.DuckDBPyConnection,
        *,
        team_stats_loader: TeamStatsLoader | None = None,
    ) -> None:
        self._conn = conn
        self._team_stats_loader = team_stats_loader or _load_team_stats_from_nflreadpy

    def refresh(self, season: int) -> TeamContextRefreshSummary:
        ensure_team_context_schema(self._conn)
        rows = self._environment_rows(season)
        upserted = 0
        for row in rows:
            self._upsert_environment_row(row)
            upserted += 1
        return TeamContextRefreshSummary(
            season=season,
            environment_rows=len(rows),
            upserted_rows=upserted,
        )

    def _environment_rows(self, season: int) -> list[dict[str, str | int | None]]:
        rows: list[dict[str, str | int | None]] = []
        for raw in self._team_stats_loader(season):
            team = _first_text(raw, ("team", "recent_team", "team_abbr", "posteam"))
            if team is None:
                continue
            pace_label = _pace_label(raw)
            pass_rate_label = _pass_rate_label(raw)
            if pace_label is None and pass_rate_label is None:
                continue
            rows.append(
                {
                    "team": team.upper(),
                    "season": season,
                    "pace_label": pace_label,
                    "pass_rate_label": pass_rate_label,
                }
            )
        return rows

    def _upsert_environment_row(self, row: dict[str, str | int | None]) -> None:
        existing = self._conn.execute(
            """
            SELECT head_coach, offensive_coordinator, play_caller, offensive_system,
                   pace_label, pass_rate_label, source, notes
            FROM team_context_by_season
            WHERE team = ? AND season = ?
            """,
            [row["team"], row["season"]],
        ).fetchone()
        if existing is None:
            values = [
                row["season"],
                row["team"],
                None,
                None,
                None,
                None,
                row["pace_label"],
                row["pass_rate_label"],
                "team_environment_nflreadpy",
                "automated team environment refresh",
            ]
        else:
            values = [
                row["season"],
                row["team"],
                existing[0],
                existing[1],
                existing[2],
                existing[3],
                existing[4] or row["pace_label"],
                existing[5] or row["pass_rate_label"],
                existing[6] or "team_environment_nflreadpy",
                _merge_notes(str(existing[7]) if existing[7] else None),
            ]
        self._conn.execute(
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
            values,
        )


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


def _load_team_stats_from_nflreadpy(season: int) -> list[Mapping[str, object]]:
    try:
        import nflreadpy  # type: ignore[import-not-found]
    except ImportError:
        return []
    loader = getattr(nflreadpy, "load_team_stats", None)
    if loader is None:
        return []
    try:
        raw = loader([season], summary_level="reg")
    except TypeError:
        raw = loader(seasons=[season], summary_level="reg")
    except Exception:
        return []
    return _rows_from_frame(raw)


def _rows_from_frame(raw: object) -> list[Mapping[str, object]]:
    if hasattr(raw, "to_dicts"):
        rows = raw.to_dicts()
        return [row for row in rows if isinstance(row, Mapping)]
    if hasattr(raw, "to_dict"):
        records = raw.to_dict("records")  # type: ignore[call-arg]
        return [row for row in records if isinstance(row, Mapping)]
    if isinstance(raw, Iterable):
        return [row for row in raw if isinstance(row, Mapping)]
    return []


def _first_text(row: Mapping[str, object], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def _pace_label(row: Mapping[str, object]) -> str | None:
    plays_per_game = _first_float(
        row,
        ("plays_per_game", "offensive_plays_per_game", "plays_pg"),
    )
    if plays_per_game is None:
        plays = _first_float(row, ("plays", "offensive_plays", "total_plays"))
        games = _first_float(row, ("games", "g"))
        if plays is not None and games not in (None, 0.0):
            plays_per_game = plays / float(games)
    if plays_per_game is None:
        return None
    if plays_per_game >= 67.0:
        return "fast"
    if plays_per_game <= 61.0:
        return "slow"
    return "neutral"


def _pass_rate_label(row: Mapping[str, object]) -> str | None:
    pass_rate = _first_float(
        row,
        ("pass_rate", "pass_rate_overall", "neutral_pass_rate"),
    )
    if pass_rate is None:
        attempts = _first_float(row, ("pass_attempts", "attempts", "att"))
        rushes = _first_float(row, ("rush_attempts", "carries", "rushes"))
        if attempts is not None and rushes is not None and attempts + rushes > 0:
            pass_rate = attempts / (attempts + rushes)
    if pass_rate is None:
        return None
    if pass_rate >= 0.60:
        return "pass_heavy"
    if pass_rate <= 0.50:
        return "run_heavy"
    return "balanced"


def _first_float(row: Mapping[str, object], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        value = row.get(key)
        if value in (None, ""):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _merge_notes(existing: str | None) -> str:
    refresh_note = "automated team environment refresh"
    if not existing:
        return refresh_note
    if refresh_note in existing:
        return existing
    return f"{existing}; {refresh_note}"


__all__ = [
    "TEAM_CONTEXT_COLUMNS",
    "TEAM_CONTEXT_DDL",
    "TeamContextImportSummary",
    "TeamContextRefreshService",
    "TeamContextRefreshSummary",
    "ensure_team_context_schema",
    "import_team_context_csv",
]
