from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends, HTTPException

from fantasy.ingestion.ingest_service import IngestService
from fantasy.ingestion.sleeper_client import SleeperClient
from fantasy.profiling.profiling_engine import ProfilingEngine
from fantasy.profiling.profiling_repo import ProfilingRepo
from fantasy.profiling.models import ManagerProfile, ManagerSummary
from fantasy.rookie_pick.rookie_pick_engine import RookiePickProfileEngine
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
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> ManagerProfile:
    repo = ProfilingRepo(conn)
    profile = ProfilingEngine(conn).compute_profile(league_id, roster_id)
    if profile.evidence_count > 0:
        repo.upsert_profile(profile)
        repo.replace_pitch_angles(profile.league_id, profile.roster_id, profile.pitch_angles)
    if profile.evidence_count == 0:
        raise HTTPException(status_code=404, detail="Manager profile not found")
    rookie_pick_profile = RookiePickProfileEngine(conn).compute_profile(league_id, roster_id)
    return profile.model_copy(
        update={
            "pick_premium_score": rookie_pick_profile.pick_premium_score,
            "pick_trade_evidence": rookie_pick_profile.pick_trade_evidence,
            "draft_selection_count": rookie_pick_profile.draft_selection_count,
            "positional_tendency": rookie_pick_profile.positional_tendency,
            "dominant_archetype": rookie_pick_profile.dominant_archetype,
            "archetype_pattern": rookie_pick_profile.archetype_pattern,
            "show_draft_picks_tab": rookie_pick_profile.show_draft_picks_tab,
            "draft_selection_history": rookie_pick_profile.draft_selection_history,
        }
    )


@router.post("/leagues/{league_id}/managers/compute")
def compute_profiles(
    league_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> dict[str, int]:
    engine = ProfilingEngine(conn)
    repo = ProfilingRepo(conn)
    profiles = engine.compute_all_profiles(league_id)
    rookie_pick_engine = RookiePickProfileEngine(conn)
    for profile in profiles:
        repo.upsert_profile(profile)
        repo.replace_pitch_angles(profile.league_id, profile.roster_id, profile.pitch_angles)
        rookie_pick_engine.compute_profile(profile.league_id, profile.roster_id)
    return {"computed": len(profiles)}


@router.post("/leagues/{league_id}/ingest/draft-picks")
async def ingest_draft_picks(
    league_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> dict[str, int]:
    async with SleeperClient() as client:
        service = IngestService(conn, client)
        return await service.ingest_draft_picks(league_id)
