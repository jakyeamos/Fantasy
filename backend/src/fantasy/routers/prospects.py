from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends

from fantasy.prospects.models import HistoricalComp, ProspectModelOutput
from fantasy.prospects.prospect_repo import ProspectRepo
from fantasy.routers.deps import get_write_db_conn

router = APIRouter(prefix="/prospects", tags=["prospects"])


@router.get("/model-outputs/{league_id}", response_model=list[ProspectModelOutput])
def get_model_outputs(
    league_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> list[ProspectModelOutput]:
    return ProspectRepo(conn).get_model_outputs(league_id)


@router.get("/comps/{player_id}", response_model=list[HistoricalComp])
def get_player_comps(
    player_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> list[HistoricalComp]:
    return ProspectRepo(conn).get_comps(player_id)
