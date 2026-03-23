from __future__ import annotations

import json
from typing import Any

import duckdb


def _loads(raw: str | None, fallback: Any) -> Any:
    if raw is None:
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


class RookieRepo:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn

    def get_league_settings(self, league_id: str) -> dict[str, Any]:
        row = self._conn.execute(
            """
            SELECT season, superflex, tep, ppr, settings_blob
            FROM leagues
            WHERE league_id = ?
            LIMIT 1
            """,
            [league_id],
        ).fetchone()
        if row is None:
            return {
                "league_id": league_id,
                "season": 2026,
                "superflex": False,
                "tep": False,
                "ppr": 0.0,
                "league_size": 12,
            }
        roster_row = self._conn.execute(
            "SELECT COUNT(*) FROM rosters WHERE league_id = ?",
            [league_id],
        ).fetchone()
        league_size = int(roster_row[0] or 12) if roster_row else 12
        settings_blob = _loads(row[4], {})
        league_size = max(int(settings_blob.get("num_teams", league_size) or league_size), 2)
        return {
            "league_id": league_id,
            "season": int(row[0] or 2026),
            "superflex": bool(row[1]),
            "tep": bool(row[2]),
            "ppr": float(row[3] or 0.0),
            "league_size": league_size,
        }

    def get_available_rookies(self, league_id: str) -> list[dict[str, Any]]:
        league_settings = self.get_league_settings(league_id)
        current_season = int(league_settings["season"])
        rows = self._conn.execute(
            """
            SELECT
                p.player_id,
                p.full_name,
                p.position,
                p.team,
                p.age,
                p.metadata_blob,
                b.adp,
                COALESCE(stats.seasons_played, 0) AS seasons_played,
                COALESCE(stats.avg_fantasy_points, 0.0) AS avg_fantasy_points
            FROM players p
            JOIN player_adp_baseline b ON b.player_id = p.player_id
            LEFT JOIN (
                SELECT
                    player_id,
                    COUNT(DISTINCT season) AS seasons_played,
                    AVG(fantasy_points) AS avg_fantasy_points
                FROM player_stats_weekly
                GROUP BY player_id
            ) stats ON stats.player_id = p.player_id
            WHERE p.position IN ('QB', 'RB', 'WR', 'TE')
            ORDER BY b.adp ASC, p.full_name ASC
            """
        ).fetchall()

        rookies: list[dict[str, Any]] = []
        for row in rows:
            metadata = _loads(row[5], {})
            draft_year = metadata.get("draft_year")
            age = int(row[4]) if row[4] is not None else None
            seasons_played = int(row[7] or 0)
            is_candidate = False
            if draft_year is not None:
                try:
                    is_candidate = int(draft_year) == current_season
                except (TypeError, ValueError):
                    is_candidate = False
            if not is_candidate and age is not None and age <= 23:
                is_candidate = True
            if not is_candidate and seasons_played == 0:
                is_candidate = True
            if not is_candidate:
                continue
            rookies.append(
                {
                    "player_id": str(row[0]),
                    "full_name": str(row[1] or row[0]),
                    "position": str(row[2] or "UNKNOWN"),
                    "team": str(row[3]) if row[3] is not None else None,
                    "age": age,
                    "metadata": metadata,
                    "adp": float(row[6] or 999.0),
                    "seasons_played": seasons_played,
                    "avg_fantasy_points": float(row[8] or 0.0),
                }
            )
        return rookies

    def save_board_cache(self, league_id: str, class_strength_signal: float, board_json: str) -> None:
        self._conn.execute("DELETE FROM rookie_board_cache WHERE league_id = ?", [league_id])
        next_id_row = self._conn.execute(
            "SELECT COALESCE(MAX(id), 0) + 1 FROM rookie_board_cache"
        ).fetchone()
        next_id = int(next_id_row[0] or 1) if next_id_row else 1
        self._conn.execute(
            """
            INSERT INTO rookie_board_cache (id, league_id, computed_at, class_strength_signal, board_json)
            VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?)
            """,
            [next_id, league_id, class_strength_signal, board_json],
        )

    def replace_league_tendencies(self, league_id: str, tendencies: list[dict[str, Any]]) -> None:
        self._conn.execute("DELETE FROM league_draft_tendencies WHERE league_id = ?", [league_id])
        next_id_row = self._conn.execute(
            "SELECT COALESCE(MAX(id), 0) + 1 FROM league_draft_tendencies"
        ).fetchone()
        next_id = int(next_id_row[0] or 1) if next_id_row else 1
        for tendency in tendencies:
            self._conn.execute(
                """
                INSERT INTO league_draft_tendencies (
                    id,
                    league_id,
                    computed_at,
                    tendency_type,
                    position,
                    player_id,
                    player_name,
                    early_draft_slots,
                    adp_delta,
                    system_value_slot
                ) VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    next_id,
                    league_id,
                    tendency.get("tendency_type"),
                    tendency.get("position"),
                    tendency.get("player_id"),
                    tendency.get("player_name"),
                    tendency.get("early_draft_slots"),
                    tendency.get("adp_delta"),
                    tendency.get("system_value_slot"),
                ],
            )
            next_id += 1

    def get_league_tendencies(self, league_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT tendency_type, position, player_id, player_name, early_draft_slots, adp_delta, system_value_slot
            FROM league_draft_tendencies
            WHERE league_id = ?
            ORDER BY tendency_type, COALESCE(position, ''), COALESCE(player_name, '')
            """,
            [league_id],
        ).fetchall()
        return [
            {
                "tendency_type": str(row[0]),
                "position": str(row[1]) if row[1] is not None else None,
                "player_id": str(row[2]) if row[2] is not None else None,
                "player_name": str(row[3]) if row[3] is not None else None,
                "early_draft_slots": float(row[4]) if row[4] is not None else None,
                "adp_delta": float(row[5]) if row[5] is not None else None,
                "system_value_slot": int(row[6]) if row[6] is not None else None,
            }
            for row in rows
        ]
