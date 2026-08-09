from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends

from fantasy.actions.command_center import CommandCenterEngine
from fantasy.decisions.adapter import decision_cards_from_actions
from fantasy.decisions.models import DecisionCardsResponse
from fantasy.routers.deps import get_read_db_conn

router = APIRouter(prefix="/v2", tags=["decisions"])


@router.get("/decisions", response_model=DecisionCardsResponse)
def get_decisions(
    league_id: str | None = None,
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> DecisionCardsResponse:
    result = CommandCenterEngine(conn).build(league_id=league_id)
    return decision_cards_from_actions(result.actions, result.computed_at)
