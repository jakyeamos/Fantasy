from __future__ import annotations

import json
from datetime import datetime, timezone

import duckdb

from fantasy.trust.models import FormatAcknowledgment


class TrustRepo:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def _next_id(self) -> int:
        row = self._conn.execute(
            "SELECT COALESCE(MAX(id), 0) + 1 FROM league_format_acknowledgments"
        ).fetchone()
        return int(row[0]) if row else 1

    def upsert_acknowledgment(
        self, league_id: str, acknowledged_rules: list[str]
    ) -> FormatAcknowledgment:
        now = datetime.now(timezone.utc).isoformat()
        rules_json = json.dumps(acknowledged_rules, separators=(",", ":"))
        self._conn.execute(
            """
            INSERT INTO league_format_acknowledgments (
                id, league_id, acknowledged_rules, acknowledged_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (league_id) DO UPDATE SET
                acknowledged_rules = EXCLUDED.acknowledged_rules,
                acknowledged_at = EXCLUDED.acknowledged_at,
                updated_at = EXCLUDED.updated_at
            """,
            [self._next_id(), league_id, rules_json, now, now],
        )
        return FormatAcknowledgment(
            league_id=league_id,
            acknowledged_rules=acknowledged_rules,
            acknowledged_at=now,
        )

    def get_acknowledgment(self, league_id: str) -> FormatAcknowledgment | None:
        row = self._conn.execute(
            """
            SELECT league_id, acknowledged_rules, CAST(acknowledged_at AS VARCHAR)
            FROM league_format_acknowledgments
            WHERE league_id = ?
            LIMIT 1
            """,
            [league_id],
        ).fetchone()
        if row is None:
            return None
        return FormatAcknowledgment(
            league_id=str(row[0]),
            acknowledged_rules=json.loads(row[1]),
            acknowledged_at=str(row[2]),
        )

    def clear_acknowledgment(self, league_id: str) -> None:
        self._conn.execute(
            "DELETE FROM league_format_acknowledgments WHERE league_id = ?",
            [league_id],
        )

