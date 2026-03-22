from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends, HTTPException

from fantasy.profiling.profiling_engine import ProfilingEngine
from fantasy.profiling.profiling_repo import ProfilingRepo
from fantasy.profiling.models import ManagerProfile, ManagerSummary
from fantasy.routers.deps import get_read_db_conn, get_write_db_conn

router = APIRouter(prefix="/profiling", tags=["profiling"])


@router.get("/leagues/{league_id}/managers", response_model=list[ManagerSummary])
def list_managers(
    league_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> list[ManagerSummary]:
    repo = ProfilingRepo(conn)
    return repo.list_manager_summaries(league_id)


@router.get(
    "/leagues/{league_id}/managers/{roster_id}",
    response_model=ManagerProfile,
)
def get_manager_profile(
    league_id: str,
    roster_id: int,
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> ManagerProfile:
    engine = ProfilingEngine(conn)
    profile = engine.compute_profile(league_id, roster_id)
    if profile.evidence_count == 0:
        raise HTTPException(status_code=404, detail="Manager profile not found")
    return profile


@router.post("/leagues/{league_id}/managers/compute")
def compute_profiles(
    league_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> dict[str, int]:
    engine = ProfilingEngine(conn)
    repo = ProfilingRepo(conn)
    profiles = engine.compute_all_profiles(league_id)
    for profile in profiles:
        repo.upsert_profile(profile)
        repo.replace_pitch_angles(profile.league_id, profile.roster_id, profile.pitch_angles)
    return {"computed": len(profiles)}
