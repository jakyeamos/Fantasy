from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import duckdb

from fantasy.context.context_repo import ContextRepo
from fantasy.context.freshness_service import FreshnessService
from fantasy.context.models import FreshnessTag
from fantasy.weekly.models import WeeklyContextRefreshResponse


TEAM_SCHEDULE_DDL = """
    CREATE TABLE IF NOT EXISTS team_schedule_weekly (
        team       VARCHAR NOT NULL,
        season     INTEGER NOT NULL,
        week       INTEGER NOT NULL,
        opponent   VARCHAR,
        is_home    BOOLEAN NOT NULL DEFAULT FALSE,
        game_date  VARCHAR,
        game_type  VARCHAR,
        loaded_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (team, season, week)
    )
"""


def _optional_nflreadpy() -> Any | None:
    try:
        import nflreadpy  # type: ignore
    except ImportError:
        return None
    return nflreadpy


def ensure_weekly_context_schema(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(TEAM_SCHEDULE_DDL)


class WeeklyPublicContextService:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn
        self._freshness = FreshnessService(ContextRepo(conn))

    def refresh(self, league_id: str, season: int | None = None) -> WeeklyContextRefreshResponse:
        ensure_weekly_context_schema(self._conn)
        active_season = season or self._league_season(league_id)
        schedule_rows = self._load_schedule_rows(active_season)
        if schedule_rows:
            self._upsert_schedule_rows(schedule_rows)

        refreshed_domains: list[str] = []
        notes = f"weekly public context refresh for {active_season}"
        if schedule_rows:
            self._freshness.mark_refreshed(
                league_id,
                "schedule",
                f"{notes}; {len(schedule_rows)} team schedule rows",
            )
            refreshed_domains.append("schedule")
        if self._has_player_metadata():
            self._freshness.mark_refreshed(league_id, "injuries", f"{notes}; Sleeper player metadata")
            refreshed_domains.append("injuries")
        if self._has_weekly_stats(active_season):
            self._freshness.mark_refreshed(league_id, "stats", f"{notes}; weekly stats present")
            self._freshness.mark_refreshed(league_id, "usage", f"{notes}; targets/carries proxy present")
            refreshed_domains.extend(["stats", "usage"])

        tags = self._freshness.get_tags(
            league_id,
            ["injuries", "usage", "schedule", "stats"],
        )
        return WeeklyContextRefreshResponse(
            league_id=league_id,
            season=active_season,
            refreshed_domains=refreshed_domains,
            schedule_rows=len(schedule_rows),
            refreshed_at=datetime.now(timezone.utc).isoformat(),
            freshness_tags=tags,
        )

    def _league_season(self, league_id: str) -> int:
        row = self._conn.execute(
            "SELECT season FROM leagues WHERE league_id = ? LIMIT 1",
            [league_id],
        ).fetchone()
        if row and row[0] is not None:
            try:
                return int(row[0])
            except (TypeError, ValueError):
                pass
        return datetime.now(timezone.utc).year

    def _load_schedule_rows(self, season: int) -> list[dict[str, Any]]:
        nflreadpy = _optional_nflreadpy()
        loader = getattr(nflreadpy, "load_schedules", None) if nflreadpy else None
        if loader is None:
            return []
        try:
            raw = loader([season])
        except TypeError:
            raw = loader(seasons=[season])
        except Exception:
            return []

        rows = raw.to_dicts() if hasattr(raw, "to_dicts") else raw.to_dict("records")
        schedule_rows: list[dict[str, Any]] = []
        for row in rows:
            try:
                game_season = int(row.get("season") or season)
                week = int(row.get("week") or 0)
            except (TypeError, ValueError):
                continue
            home_team = row.get("home_team")
            away_team = row.get("away_team")
            if week <= 0 or not home_team or not away_team:
                continue
            game_date = row.get("gameday") or row.get("game_date")
            game_type = row.get("game_type")
            schedule_rows.append(
                {
                    "team": str(home_team),
                    "season": game_season,
                    "week": week,
                    "opponent": str(away_team),
                    "is_home": True,
                    "game_date": str(game_date) if game_date is not None else None,
                    "game_type": str(game_type) if game_type is not None else None,
                }
            )
            schedule_rows.append(
                {
                    "team": str(away_team),
                    "season": game_season,
                    "week": week,
                    "opponent": str(home_team),
                    "is_home": False,
                    "game_date": str(game_date) if game_date is not None else None,
                    "game_type": str(game_type) if game_type is not None else None,
                }
            )
        return schedule_rows

    def _upsert_schedule_rows(self, rows: list[dict[str, Any]]) -> None:
        loaded_at = datetime.now(timezone.utc)
        self._conn.executemany(
            """
            INSERT INTO team_schedule_weekly (
                team, season, week, opponent, is_home, game_date, game_type, loaded_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (team, season, week) DO UPDATE SET
                opponent = EXCLUDED.opponent,
                is_home = EXCLUDED.is_home,
                game_date = EXCLUDED.game_date,
                game_type = EXCLUDED.game_type,
                loaded_at = EXCLUDED.loaded_at
            """,
            [
                [
                    row["team"],
                    row["season"],
                    row["week"],
                    row["opponent"],
                    row["is_home"],
                    row["game_date"],
                    row["game_type"],
                    loaded_at,
                ]
                for row in rows
            ],
        )

    def _has_player_metadata(self) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM players WHERE refreshed_at IS NOT NULL LIMIT 1"
        ).fetchone()
        return row is not None

    def _has_weekly_stats(self, season: int) -> bool:
        row = self._conn.execute(
            """
            SELECT 1
            FROM player_stats_weekly
            WHERE season = ?
              AND (
                fantasy_points IS NOT NULL
                OR targets IS NOT NULL
                OR carries IS NOT NULL
                OR passing_yards IS NOT NULL
              )
            LIMIT 1
            """,
            [season],
        ).fetchone()
        return row is not None
