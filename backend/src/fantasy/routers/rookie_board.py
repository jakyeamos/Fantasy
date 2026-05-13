from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from fantasy.context.calendar_service import CalendarService
from fantasy.context.constants import CALENDAR_GUIDANCE
from fantasy.context.context_repo import ContextRepo
from fantasy.context.freshness_service import FreshnessService
from fantasy.context.models import RecommendationContext
from fantasy.rookie.models import RookieBoardResult
from fantasy.rookie.rookie_engine import RookieEngine
from fantasy.routers.deps import get_write_db_conn

router = APIRouter(prefix="/rookie-board", tags=["rookie-board"])


class RookieBoardWithContext(BaseModel):
    rookie_board: RookieBoardResult
    recommendation_context: RecommendationContext


def _build_recommendation_context(
    conn: duckdb.DuckDBPyConnection,
    league_id: str,
) -> RecommendationContext:
    repo = ContextRepo(conn)
    calendar_context = CalendarService(repo=repo).get_context(league_id)
    try:
        freshness_tags = FreshnessService(repo=repo).get_tags(
            league_id,
            ["injuries", "draft_capital", "landing_spots"],
        )
    except duckdb.Error:
        freshness_tags = []
    note = CALENDAR_GUIDANCE.get((calendar_context.active_state, "general"))
    return RecommendationContext(
        calendar_state=calendar_context.active_state,
        freshness_tags=[tag for tag in freshness_tags if tag.is_stale],
        calendar_note=note,
    )


@router.get("/{league_id}", response_model=RookieBoardWithContext)
def get_rookie_board(
    league_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> RookieBoardWithContext:
    return RookieBoardWithContext(
        rookie_board=RookieEngine(conn).compute_board(league_id),
        recommendation_context=_build_recommendation_context(conn, league_id),
    )
