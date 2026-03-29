from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends

from fantasy.rookie.models import DraftRoomResult
from fantasy.rookie.rookie_engine import RookieEngine
from fantasy.rookie_pick.rookie_pick_engine import RookiePickProfileEngine
from fantasy.routers.deps import get_write_db_conn

router = APIRouter(prefix="/draft-room", tags=["draft-room"])


@router.get("/{league_id}/{pick_slot}", response_model=DraftRoomResult)
def get_draft_room(
    league_id: str,
    pick_slot: int,
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> DraftRoomResult:
    result = RookieEngine(conn).compute_draft_room(league_id, pick_slot)
    result.tendency_warnings.extend(
        RookiePickProfileEngine(conn).compute_tendency_warnings(league_id)
    )
    return result
