from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends

from fantasy.routers.deps import get_read_db_conn
from fantasy.weekly.models import WeeklyEdgeResponse
from fantasy.weekly.weekly_edge_service import WeeklyEdgeService

router = APIRouter(prefix="/weekly", tags=["weekly"])


@router.get("/league/{league_id}/{roster_id}/edge", response_model=WeeklyEdgeResponse)
def get_weekly_edge(
    league_id: str,
    roster_id: int,
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> WeeklyEdgeResponse:
    return WeeklyEdgeService(conn).build(league_id, roster_id)

