from __future__ import annotations

import json
from typing import Any, Sequence

import duckdb

from fantasy.player_flags.models import PlayerContextFlag


def _loads(raw: str | None, fallback: Any) -> Any:
    if raw is None:
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


class FlagRepo:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn

    def _next_id(self) -> int:
        row = self._conn.execute(
            "SELECT COALESCE(MAX(id), 0) + 1 FROM player_context_flags"
        ).fetchone()
        return int(row[0]) if row else 1

    def upsert_flag(self, flag: PlayerContextFlag) -> PlayerContextFlag:
        existing = self._conn.execute(
            """
            SELECT id
            FROM player_context_flags
            WHERE player_id = ? AND flag_type = ?
            LIMIT 1
            """,
            [flag.player_id, flag.flag_type],
        ).fetchone()
        row_id = int(existing[0]) if existing else self._next_id()
        self._conn.execute(
            """
            INSERT INTO player_context_flags (
                id, player_id, flag_type, expires_at, source, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (player_id, flag_type) DO UPDATE SET
                created_at = now(),
                expires_at = EXCLUDED.expires_at,
                source = EXCLUDED.source,
                metadata_json = EXCLUDED.metadata_json
            """,
            [
                row_id,
                flag.player_id,
                flag.flag_type,
                flag.expires_at,
                flag.source,
                json.dumps(flag.metadata, separators=(",", ":")),
            ],
        )
        return flag

    def clear_flags(self, player_id: str, flag_types: Sequence[str] | None = None) -> None:
        if flag_types:
            placeholders = ",".join("?" for _ in flag_types)
            self._conn.execute(
                f"""
                DELETE FROM player_context_flags
                WHERE player_id = ?
                  AND flag_type IN ({placeholders})
                """,
                [player_id, *flag_types],
            )
            return
        self._conn.execute(
            "DELETE FROM player_context_flags WHERE player_id = ?",
            [player_id],
        )

    def get_active_flags(self, player_id: str) -> list[PlayerContextFlag]:
        rows = self._conn.execute(
            """
            SELECT player_id, flag_type, CAST(created_at AS VARCHAR), CAST(expires_at AS VARCHAR),
                   source, metadata_json
            FROM player_context_flags
            WHERE player_id = ?
              AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            ORDER BY created_at DESC
            """,
            [player_id],
        ).fetchall()
        return [
            PlayerContextFlag(
                player_id=str(row[0]),
                flag_type=str(row[1]),
                created_at=str(row[2]) if row[2] is not None else None,
                expires_at=str(row[3]) if row[3] is not None else None,
                source=str(row[4] or "sleeper_ingest"),
                metadata=_loads(row[5], {}),
            )
            for row in rows
        ]


__all__ = ["FlagRepo"]
