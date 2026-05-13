from __future__ import annotations

from datetime import date

import duckdb
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from fantasy.prospects.models import HistoricalComp, ProspectModelOutput
from fantasy.prospects.draft_capital_refresh import refresh_actual_draft_capital
from fantasy.prospects.prospect_repo import ProspectRepo
from fantasy.routers.deps import get_write_db_conn

router = APIRouter(prefix="/prospects", tags=["prospects"])


class DraftCapitalRefreshResponse(BaseModel):
    draft_year: int
    source_rows: int
    matched_rows: int
    updated_rows: int
    unmatched_rows: int
    rebuilt_boards: int


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


@router.post("/draft-capital/refresh", response_model=DraftCapitalRefreshResponse)
def refresh_draft_capital(
    draft_year: int | None = Query(default=None, ge=2000, le=2100),
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> DraftCapitalRefreshResponse:
    result = refresh_actual_draft_capital(conn, draft_year=draft_year or date.today().year)
    return DraftCapitalRefreshResponse(**result)
