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
            SELECT league_id, domain, last_updated, notes,
                   fetched_at, observed_at, effective_at, coverage_through,
                   status, source_id, record_count
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
                fetched_at=row[4],
                observed_at=row[5],
                effective_at=row[6],
                coverage_through=row[7],
                status=str(row[8] or "unknown"),
                source_id=str(row[9]) if row[9] is not None else None,
                record_count=int(row[10]) if row[10] is not None else None,
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

    def record_source_result(
        self,
        *,
        league_id: str,
        domain: str,
        fetched_at: datetime,
        source_id: str,
        parsed_successfully: bool,
        record_count: int,
        authoritative_empty: bool = False,
        observed_at: datetime | None = None,
        effective_at: datetime | None = None,
        coverage_through: datetime | None = None,
        notes: str | None = None,
    ) -> FreshnessRow:
        """Record a fetch without letting failed/empty fetches erase last-good truth."""

        existing = self.get_freshness_rows(league_id, [domain]).get(domain)
        confirmed = parsed_successfully and (record_count > 0 or authoritative_empty)
        last_updated = fetched_at if confirmed else (existing.last_updated if existing else None)
        row_id_result = self._conn.execute(
            "SELECT id FROM freshness_domains WHERE league_id = ? AND domain = ?",
            [league_id, domain],
        ).fetchone()
        row_id = int(row_id_result[0]) if row_id_result else self._next_id("freshness_domains")
        status = "fresh" if confirmed else "degraded"
        resolved_observed = observed_at if confirmed else (existing.observed_at if existing else None)
        resolved_effective = effective_at if confirmed else (existing.effective_at if existing else None)
        resolved_coverage = (
            coverage_through if confirmed else (existing.coverage_through if existing else None)
        )
        self._conn.execute(
            """
            INSERT INTO freshness_domains (
                id, league_id, domain, last_updated, notes, fetched_at,
                observed_at, effective_at, coverage_through, status, source_id,
                record_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (league_id, domain) DO UPDATE SET
                last_updated = EXCLUDED.last_updated,
                notes = EXCLUDED.notes,
                fetched_at = EXCLUDED.fetched_at,
                observed_at = EXCLUDED.observed_at,
                effective_at = EXCLUDED.effective_at,
                coverage_through = EXCLUDED.coverage_through,
                status = EXCLUDED.status,
                source_id = EXCLUDED.source_id,
                record_count = EXCLUDED.record_count
            """,
            [
                row_id,
                league_id,
                domain,
                last_updated,
                notes,
                fetched_at,
                resolved_observed,
                resolved_effective,
                resolved_coverage,
                status,
                source_id,
                record_count,
            ],
        )
        return FreshnessRow(
            league_id=league_id,
            domain=domain,
            last_updated=last_updated,
            notes=notes,
            fetched_at=fetched_at,
            observed_at=resolved_observed,
            effective_at=resolved_effective,
            coverage_through=resolved_coverage,
            status=status,
            source_id=source_id,
            record_count=record_count,
        )
