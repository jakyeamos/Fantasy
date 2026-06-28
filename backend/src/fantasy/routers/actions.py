from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends

from fantasy.actions.command_center import CommandCenterEngine
from fantasy.actions.models import CommandCenterResponse
from fantasy.routers.deps import get_write_db_conn

router = APIRouter(prefix="/actions", tags=["actions"])


@router.get("/command-center", response_model=CommandCenterResponse)
def get_command_center(
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> CommandCenterResponse:
    return CommandCenterEngine(conn).build()


@router.get("/league/{league_id}", response_model=CommandCenterResponse)
def get_league_actions(
    league_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> CommandCenterResponse:
    return CommandCenterEngine(conn).build(league_id=league_id)


@router.post("/recompute", response_model=CommandCenterResponse)
def recompute_actions(
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> CommandCenterResponse:
    return CommandCenterEngine(conn).recompute()
