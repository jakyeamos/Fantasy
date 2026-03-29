from __future__ import annotations

from datetime import datetime, timedelta, timezone

import duckdb

from fantasy.context.constants import OVERRIDE_TTL_DAYS
from fantasy.context.models import FreshnessRow


class ContextRepo:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def _next_id(self, table: str) -> int:
        row = self._conn.execute(
            f"SELECT COALESCE(MAX(id), 0) + 1 FROM {table}"
        ).fetchone()
        return int(row[0])

    def upsert_override(
        self,
        league_id: str,
        state: str,
        expires_at: datetime | None = None,
        set_by: str = "user",
    ) -> None:
        expiry = expires_at or (
            datetime.now(tz=timezone.utc) + timedelta(days=OVERRIDE_TTL_DAYS)
        )
        existing = self._conn.execute(
            """
            SELECT id
            FROM calendar_overrides
            WHERE league_id = ?
            """,
            [league_id],
        ).fetchone()
        row_id = int(existing[0]) if existing else self._next_id("calendar_overrides")
        self._conn.execute(
            """
            INSERT INTO calendar_overrides (id, league_id, state, set_by, set_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (league_id) DO UPDATE SET
                state = EXCLUDED.state,
                set_by = EXCLUDED.set_by,
                set_at = EXCLUDED.set_at,
                expires_at = EXCLUDED.expires_at
            """,
            [row_id, league_id, state, set_by, datetime.now(tz=timezone.utc), expiry],
        )

    def get_override(self, league_id: str) -> str | None:
        row = self._conn.execute(
            """
            SELECT state, expires_at
            FROM calendar_overrides
            WHERE league_id = ?
            LIMIT 1
            """,
            [league_id],
        ).fetchone()
        if row is None:
            return None
        expires_at = row[1]
        if expires_at is not None:
            expires_dt = expires_at.replace(tzinfo=timezone.utc)
            if expires_dt < datetime.now(tz=timezone.utc):
                self.clear_override(league_id)
                return None
        return str(row[0])

    def clear_override(self, league_id: str) -> None:
        self._conn.execute(
            """
            DELETE FROM calendar_overrides
            WHERE league_id = ?
            """,
            [league_id],
        )

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
