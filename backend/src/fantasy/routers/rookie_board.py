from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends

from fantasy.rookie.models import RookieBoardResult
from fantasy.rookie.rookie_engine import RookieEngine
from fantasy.routers.deps import get_write_db_conn

router = APIRouter(prefix="/rookie-board", tags=["rookie-board"])


@router.get("/{league_id}", response_model=RookieBoardResult)
def get_rookie_board(
    league_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> RookieBoardResult:
    return RookieEngine(conn).compute_board(league_id)
