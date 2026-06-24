from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends

from fantasy.context.calendar_service import CalendarService
from fantasy.context.constants import CALENDAR_GUIDANCE
from fantasy.context.context_repo import ContextRepo
from fantasy.context.freshness_service import FreshnessService
from fantasy.context.models import RecommendationContext
from fantasy.routers.deps import get_read_db_conn, get_write_db_conn
from fantasy.trade.models import (
    PickSearchResult,
    PlayerSearchResult,
    TradeRosterResult,
    TradeEvaluation,
    TradeRequest,
)
from fantasy.trade.package_builder import PackageBuilder
from fantasy.trade.reroute_engine import RerouteEngine
from fantasy.trade.trade_engine import TradeEngine
from fantasy.trade.trade_repo import TradeRepo

router = APIRouter(prefix="/trade", tags=["trade"])


def _build_recommendation_context(
    conn: duckdb.DuckDBPyConnection,
    league_id: str,
) -> RecommendationContext:
    repo = ContextRepo(conn)
    calendar_context = CalendarService(repo=repo).get_context(league_id)
    freshness_tags = FreshnessService(repo=repo).get_tags(
        league_id,
        ["injuries", "depth_chart", "free_agency"],
    )
    note = CALENDAR_GUIDANCE.get((calendar_context.active_state, "general"))
    return RecommendationContext(
        calendar_state=calendar_context.active_state,
        freshness_tags=[tag for tag in freshness_tags if tag.is_stale],
        calendar_note=note,
    )


@router.post("/evaluate", response_model=TradeEvaluation)
def evaluate_trade(
    request: TradeRequest,
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> TradeEvaluation:
    engine = TradeEngine(conn)
    evaluation = engine.evaluate(request)
    if request.include_reroutes:
        evaluation.reroutes = RerouteEngine(conn).generate(request, evaluation)
    if request.include_package:
        evaluation.package = PackageBuilder(conn).build(request, evaluation)
    evaluation.recommendation_context = _build_recommendation_context(
        conn,
        request.league_id,
    )
    return evaluation


@router.get("/players/search", response_model=list[PlayerSearchResult])
def search_players(
    league_id: str,
    q: str = "",
    roster_id: int | None = None,
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> list[PlayerSearchResult]:
    repo = TradeRepo(conn)
    return [PlayerSearchResult(**row) for row in repo.search_players(league_id, q, roster_id)]


@router.get("/picks/search", response_model=list[PickSearchResult])
def search_picks(
    league_id: str,
    roster_id: int | None = None,
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> list[PickSearchResult]:
    repo = TradeRepo(conn)
    return [PickSearchResult(**row) for row in repo.get_picks_for_league(league_id, roster_id)]


@router.get("/rosters", response_model=list[TradeRosterResult])
def list_rosters(
    league_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> list[TradeRosterResult]:
    repo = TradeRepo(conn)
    return [TradeRosterResult(**row) for row in repo.get_rosters(league_id)]
