from __future__ import annotations

import json
from typing import Any

import duckdb
from fastapi import APIRouter, Depends

from fantasy.routers.deps import get_read_db_conn

router = APIRouter(prefix="/health", tags=["health"])


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
