from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends

from fantasy.routers.deps import get_read_db_conn, get_write_db_conn
from fantasy.trade.models import (
    PickSearchResult,
    PlayerSearchResult,
    TradeEvaluation,
    TradeRequest,
)
from fantasy.trade.package_builder import PackageBuilder
from fantasy.trade.reroute_engine import RerouteEngine
from fantasy.trade.trade_engine import TradeEngine
from fantasy.trade.trade_repo import TradeRepo

router = APIRouter(prefix="/trade", tags=["trade"])


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
    return evaluation


@router.get("/players/search", response_model=list[PlayerSearchResult])
def search_players(
    league_id: str,
    q: str,
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
