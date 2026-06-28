from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends, Query

from fantasy.edge_radar.engine import EdgeRadarEngine
from fantasy.edge_radar.models import EdgeRadarResponse, EdgeSignalType
from fantasy.routers.deps import get_read_db_conn

router = APIRouter(prefix="/edge-radar", tags=["edge-radar"])


@router.get("", response_model=EdgeRadarResponse)
def get_edge_radar(
    league_id: str | None = None,
    signal_type: EdgeSignalType | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> EdgeRadarResponse:
    return EdgeRadarEngine(conn).build(
        league_id=league_id,
        signal_type=signal_type,
        limit=limit,
    )
