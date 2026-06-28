from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends

from fantasy.routers.deps import get_read_db_conn, get_write_db_conn
from fantasy.weekly.models import WeeklyContextRefreshResponse, WeeklyEdgeResponse
from fantasy.weekly.public_context import WeeklyPublicContextService
from fantasy.weekly.weekly_edge_service import WeeklyEdgeService

router = APIRouter(prefix="/weekly", tags=["weekly"])


@router.get("/league/{league_id}/{roster_id}/edge", response_model=WeeklyEdgeResponse)
def get_weekly_edge(
    league_id: str,
    roster_id: int,
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> WeeklyEdgeResponse:
    return WeeklyEdgeService(conn).build(league_id, roster_id)


@router.post("/league/{league_id}/refresh-context", response_model=WeeklyContextRefreshResponse)
def refresh_weekly_context(
    league_id: str,
    season: int | None = None,
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> WeeklyContextRefreshResponse:
    return WeeklyPublicContextService(conn).refresh(league_id, season)
