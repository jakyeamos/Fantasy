from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends, HTTPException

from fantasy.routers.deps import get_write_db_conn
from fantasy.waiver.models import StartupContext
from fantasy.waiver.startup_engine import StartupEngine
from fantasy.waiver.waiver_repo import WaiverRepo

router = APIRouter(prefix="/startup", tags=["startup"])


@router.get("/{league_id}/context", response_model=StartupContext)
def get_startup_context(
    league_id: str,
    roster_id: int = 0,
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> StartupContext:
    try:
        context = StartupEngine(conn).compute_context(league_id, roster_id)
        WaiverRepo(conn).upsert_startup_context(context)
        return context
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
