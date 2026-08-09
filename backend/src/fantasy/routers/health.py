from __future__ import annotations

import json
from typing import Any

import duckdb
from fastapi import APIRouter, Depends, HTTPException

from fantasy.routers.deps import get_read_db_conn

router = APIRouter(prefix="/health", tags=["health"])
process_router = APIRouter(tags=["health"])


@process_router.get("/healthz")
def get_process_health() -> dict[str, str]:
    """Return a process-level liveness result without touching application data."""

    return {"status": "ok", "service": "fantasy-backend"}


@process_router.get("/readyz")
def get_process_readiness(
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> dict[str, object]:
    """Return readiness only when DuckDB and required runtime tables are usable."""

    try:
        conn.execute("SELECT 1").fetchone()
        tables = {
            row[0]
            for row in conn.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'main'
                """
            ).fetchall()
        }
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={"status": "not_ready", "reason": "database_unavailable"},
        ) from exc

    required_tables = {"ingest_runs", "leagues", "players", "rosters"}
    missing_tables = sorted(required_tables - tables)
    if missing_tables:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "reason": "required_tables_missing",
                "missing_tables": missing_tables,
            },
        )

    return {
        "status": "ready",
        "service": "fantasy-backend",
        "database": "ok",
        "required_tables": sorted(required_tables),
    }


@router.get("/{league_id}")
def get_health(
    league_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> dict[str, Any]:
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
        return {
            "league_id": league_id,
            "last_run_at": None,
            "status": None,
            "gap_count": 0,
            "gaps": [],
        }

    try:
        gaps = json.loads(row[2]) if row[2] else []
    except json.JSONDecodeError:
        gaps = []

    return {
        "league_id": league_id,
        "last_run_at": row[1].isoformat() if row[1] else None,
        "status": row[0],
        "gap_count": len(gaps),
        "gaps": gaps,
    }
