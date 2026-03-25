from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from fantasy.intelligence.intelligence_service import IntelligenceService
from fantasy.intelligence.models import DirectionResult, PlayerValue, TeamScorecard
from fantasy.lineup.models import HygieneResult, LineupResult
from fantasy.routers.deps import get_read_db_conn, get_write_db_conn

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


class ComputeResponse(BaseModel):
    league_id: str
    roster_count: int
    player_value_count: int


@router.post("/compute/{league_id}", response_model=ComputeResponse)
def compute_intelligence(
    league_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> ComputeResponse:
    service = IntelligenceService(conn)
    result = service.compute_league(league_id)
    player_value_count = sum(len(values) for values in result["values"].values())
    return ComputeResponse(
        league_id=league_id,
        roster_count=len(result["scorecards"]),
        player_value_count=player_value_count,
    )


@router.get("/scorecard/{league_id}/{roster_id}", response_model=TeamScorecard)
def get_scorecard(
    league_id: str,
    roster_id: int,
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> TeamScorecard:
    service = IntelligenceService(conn)
    return service.get_scorecard(league_id, roster_id)


@router.get("/direction/{league_id}/{roster_id}", response_model=DirectionResult)
def get_direction(
    league_id: str,
    roster_id: int,
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> DirectionResult:
    service = IntelligenceService(conn)
    return service.get_direction(league_id, roster_id)


@router.get("/player-value/{league_id}/{roster_id}/{player_id}", response_model=PlayerValue)
def get_player_value(
    league_id: str,
    roster_id: int,
    player_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> PlayerValue:
    service = IntelligenceService(conn)
    return service.get_player_value(league_id, roster_id, player_id)


@router.get("/lineup/{league_id}/{roster_id}", response_model=LineupResult)
def get_lineup(
    league_id: str,
    roster_id: int,
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> LineupResult:
    service = IntelligenceService(conn)
    return service.get_lineup_result(league_id, roster_id)


@router.get("/hygiene/{league_id}/{roster_id}", response_model=HygieneResult)
def get_hygiene(
    league_id: str,
    roster_id: int,
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> HygieneResult:
    service = IntelligenceService(conn)
    return service.get_hygiene_result(league_id, roster_id)
