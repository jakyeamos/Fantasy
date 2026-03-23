from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends

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


@router.post("/evaluate", response_model=TradeEvaluation)
def evaluate_trade(
    request: TradeRequest,
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> TradeEvaluation:
    engine = TradeEngine(conn)
    evaluation = engine.evaluate(request)
    has_multi_team_context = bool(request.third_party_trades)
    if request.include_reroutes and not has_multi_team_context:
        evaluation.reroutes = RerouteEngine(conn).generate(request, evaluation)
    if request.include_package and not has_multi_team_context:
        evaluation.package = PackageBuilder(conn).build(request, evaluation)
    if has_multi_team_context:
        evaluation.strategic_distinction.explanation += (
            " Reroutes and package builder are disabled for multi-team deals until "
            "those helpers can model sidecar legs explicitly."
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
