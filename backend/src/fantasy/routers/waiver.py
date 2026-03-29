from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends, HTTPException

from fantasy.routers.deps import get_write_db_conn
from fantasy.waiver.models import ActionPlan, OrphanIntake, WaiverRecommendationsResponse
from fantasy.waiver.orphan_engine import OrphanEngine
from fantasy.waiver.waiver_engine import WaiverEngine
from fantasy.waiver.waiver_repo import WaiverRepo

router = APIRouter(prefix="/waiver", tags=["waiver"])


@router.get("/{league_id}/{roster_id}/recommendations", response_model=WaiverRecommendationsResponse)
def get_waiver_recommendations(
    league_id: str,
    roster_id: int,
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> WaiverRecommendationsResponse:
    try:
        result = WaiverEngine(conn).compute_recommendations(league_id, roster_id)
        WaiverRepo(conn).upsert_waiver_recommendations(result)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{league_id}/{roster_id}/orphan-intake", response_model=OrphanIntake)
def run_orphan_intake(
    league_id: str,
    roster_id: int,
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> OrphanIntake:
    try:
        intake = OrphanEngine(conn).compute_intake(league_id, roster_id)
        WaiverRepo(conn).upsert_orphan_intake(intake)
        return intake
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{league_id}/{roster_id}/action-plan", response_model=ActionPlan)
def get_action_plan(
    league_id: str,
    roster_id: int,
    plan_type: str = "orphan_intake",
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> ActionPlan:
    try:
        plan = OrphanEngine(conn).generate_action_plan(league_id, roster_id, plan_type)
        WaiverRepo(conn).upsert_action_plan(plan)
        return plan
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
