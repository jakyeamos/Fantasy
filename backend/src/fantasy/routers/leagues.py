from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends

from fantasy.lineup.lineup_repo import LineupRepo
from fantasy.lineup.models import LeagueTaxiConfig
from fantasy.routers.deps import get_read_db_conn, get_write_db_conn

router = APIRouter(prefix="/leagues", tags=["leagues"])


@router.get("/{league_id}/taxi-config")
def get_taxi_config(
    league_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> dict:
    repo = LineupRepo(conn)
    config = repo.get_taxi_config(league_id)
    return {"league_id": league_id, "config": config}


@router.put("/{league_id}/taxi-config")
def save_taxi_config(
    league_id: str,
    body: LeagueTaxiConfig,
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> dict:
    repo = LineupRepo(conn)
    saved = repo.save_taxi_config(league_id, body)
    return {"league_id": league_id, "config": saved}


@router.get("/{league_id}/slot-occupancy/{roster_id}")
def get_slot_occupancy(
    league_id: str,
    roster_id: int,
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> dict:
    repo = LineupRepo(conn)
    return repo.get_slot_occupancy(league_id, roster_id)
