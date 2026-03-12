from __future__ import annotations

import json
from typing import Any

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from fantasy.ingestion.ingest_service import IngestService
from fantasy.ingestion.sleeper_client import SleeperClient
from fantasy.routers.deps import get_read_db_conn, get_write_db_conn

router = APIRouter(prefix="/ingest", tags=["ingest"])


class IngestRunResponse(BaseModel):
    run_id: int
    league_id: str
    status: str


class IngestStatusResponse(BaseModel):
    league_id: str
    last_run_status: str | None
    last_run_at: str | None
    gap_count: int
    gaps: list[dict[str, Any]]


@router.post("/{league_id}", response_model=IngestRunResponse)
async def trigger_ingest(
    league_id: str,
    run_type: str = Query(default="full", pattern="^(full|incremental)$"),
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> IngestRunResponse:
    try:
        async with SleeperClient() as client:
            service = IngestService(conn, client)
            run_id = await service.run(league_id, run_type)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail={"detail": "ingest_in_progress", "league_id": league_id},
        ) from exc

    row = conn.execute("SELECT status FROM ingest_runs WHERE id = ?", [run_id]).fetchone()
    status = row[0] if row else "complete"
    return IngestRunResponse(run_id=run_id, league_id=league_id, status=status)


@router.get("/status/{league_id}", response_model=IngestStatusResponse)
def get_ingest_status(
    league_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> IngestStatusResponse:
    row = conn.execute(
        """
        SELECT status, completed_at, gaps_json
        FROM ingest_runs
        WHERE league_id = ?
        ORDER BY started_at DESC
        LIMIT 1
        """,
        [league_id],
    ).fetchone()

    if row is None:
        return IngestStatusResponse(
            league_id=league_id,
            last_run_status=None,
            last_run_at=None,
            gap_count=0,
            gaps=[],
        )

    try:
        gaps = json.loads(row[2]) if row[2] else []
    except json.JSONDecodeError:
        gaps = []

    return IngestStatusResponse(
        league_id=league_id,
        last_run_status=row[0],
        last_run_at=row[1].isoformat() if row[1] else None,
        gap_count=len(gaps),
        gaps=gaps,
    )
