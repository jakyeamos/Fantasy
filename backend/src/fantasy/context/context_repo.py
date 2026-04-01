from __future__ import annotations

from datetime import datetime

import duckdb

from fantasy.context.models import FreshnessRow


class ContextRepo:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def _next_id(self, table: str) -> int:
        row = self._conn.execute(
            f"SELECT COALESCE(MAX(id), 0) + 1 FROM {table}"
        ).fetchone()
        return int(row[0])

    def get_freshness_rows(
        self, league_id: str, domains: list[str]
    ) -> dict[str, FreshnessRow]:
        if not domains:
            return {}
        rows = self._conn.execute(
            """
            SELECT league_id, domain, last_updated, notes
            FROM freshness_domains
            WHERE league_id = ? AND domain IN (SELECT UNNEST(?))
            """,
            [league_id, domains],
        ).fetchall()
        return {
            str(row[1]): FreshnessRow(
                league_id=str(row[0]),
                domain=str(row[1]),
                last_updated=row[2],
                notes=str(row[3]) if row[3] is not None else None,
            )
            for row in rows
        }

    def upsert_freshness(
        self,
        league_id: str,
        domain: str,
        last_updated: datetime,
        notes: str | None = None,
    ) -> None:
        existing = self._conn.execute(
            """
            SELECT id
            FROM freshness_domains
            WHERE league_id = ? AND domain = ?
            """,
            [league_id, domain],
        ).fetchone()
        row_id = int(existing[0]) if existing else self._next_id("freshness_domains")
        self._conn.execute(
            """
            INSERT INTO freshness_domains (id, league_id, domain, last_updated, notes)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (league_id, domain) DO UPDATE SET
                last_updated = EXCLUDED.last_updated,
                notes = EXCLUDED.notes
            """,
            [row_id, league_id, domain, last_updated, notes],
        )
