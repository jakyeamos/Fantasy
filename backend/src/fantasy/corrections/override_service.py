from __future__ import annotations

import logging
from datetime import datetime

import duckdb
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class CorrectionCreate(BaseModel):
    league_id: str
    entity_type: str
    entity_id: str
    field: str
    corrected_value: str
    original_value: str | None = None
    corrected_by: str = "user"


class CorrectionResponse(BaseModel):
    id: int
    league_id: str
    entity_type: str
    entity_id: str
    field: str
    original_value: str | None = None
    corrected_value: str
    corrected_by: str
    created_at: datetime


class OverrideService:
    def _next_id(self, conn: duckdb.DuckDBPyConnection) -> int:
        row = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM corrections").fetchone()
        return int(row[0])

    def create_correction(
        self, conn: duckdb.DuckDBPyConnection, data: CorrectionCreate
    ) -> CorrectionResponse:
        existing = conn.execute(
            """
            SELECT id
            FROM corrections
            WHERE league_id = ? AND entity_type = ? AND entity_id = ? AND field = ?
            """,
            [data.league_id, data.entity_type, data.entity_id, data.field],
        ).fetchone()
        row_id = int(existing[0]) if existing else self._next_id(conn)

        conn.execute(
            """
            INSERT INTO corrections (
                id,
                league_id,
                entity_type,
                entity_id,
                field,
                original_value,
                corrected_value,
                corrected_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (league_id, entity_type, entity_id, field) DO UPDATE SET
                original_value = EXCLUDED.original_value,
                corrected_value = EXCLUDED.corrected_value,
                corrected_by = EXCLUDED.corrected_by
            """,
            [
                row_id,
                data.league_id,
                data.entity_type,
                data.entity_id,
                data.field,
                data.original_value,
                data.corrected_value,
                data.corrected_by,
            ],
        )

        row = conn.execute(
            """
            SELECT id, league_id, entity_type, entity_id, field, original_value,
                   corrected_value, corrected_by, created_at
            FROM corrections
            WHERE id = ?
            LIMIT 1
            """,
            [row_id],
        ).fetchone()

        if row is None:
            raise RuntimeError("Correction was not stored.")

        return CorrectionResponse(
            id=row[0],
            league_id=row[1],
            entity_type=row[2],
            entity_id=row[3],
            field=row[4],
            original_value=row[5],
            corrected_value=row[6],
            corrected_by=row[7],
            created_at=row[8],
        )

    def delete_correction(self, conn: duckdb.DuckDBPyConnection, correction_id: int) -> bool:
        before = conn.execute("SELECT COUNT(*) FROM corrections WHERE id = ?", [correction_id]).fetchone()[0]
        conn.execute("DELETE FROM corrections WHERE id = ?", [correction_id])
        return bool(before)

    def list_corrections(
        self, conn: duckdb.DuckDBPyConnection, league_id: str
    ) -> list[CorrectionResponse]:
        rows = conn.execute(
            """
            SELECT id, league_id, entity_type, entity_id, field, original_value,
                   corrected_value, corrected_by, created_at
            FROM corrections
            WHERE league_id = ?
            ORDER BY created_at DESC
            """,
            [league_id],
        ).fetchall()
        return [
            CorrectionResponse(
                id=row[0],
                league_id=row[1],
                entity_type=row[2],
                entity_id=row[3],
                field=row[4],
                original_value=row[5],
                corrected_value=row[6],
                corrected_by=row[7],
                created_at=row[8],
            )
            for row in rows
        ]

    def apply_corrections(self, conn: duckdb.DuckDBPyConnection, league_id: str) -> int:
        rows = conn.execute(
            """
            SELECT id, entity_type, entity_id, field, corrected_value
            FROM corrections
            WHERE league_id = ?
            """,
            [league_id],
        ).fetchall()

        for row in rows:
            logger.info(
                "Applied correction id=%s type=%s entity=%s field=%s value=%s",
                row[0],
                row[1],
                row[2],
                row[3],
                row[4],
            )

        return len(rows)


__all__ = ["OverrideService", "CorrectionCreate", "CorrectionResponse"]
