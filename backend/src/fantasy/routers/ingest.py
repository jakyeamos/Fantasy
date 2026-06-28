from __future__ import annotations

import json
from typing import Any

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from fantasy.edge_radar.team_context import TeamContextRefreshService
from fantasy.ingestion.ingest_service import IngestService
from fantasy.ingestion.nfl_data_loader import refresh_adp_baseline_from_fantasycalc
from fantasy.market.models import FantasyCalcUnavailableError
from fantasy.prospects.draft_capital_refresh import refresh_actual_draft_capital
from fantasy.ingestion.sleeper_client import SleeperClient
from fantasy.startup_tasks import refresh_league_artifacts
from fantasy.routers.deps import get_read_db_conn, get_write_db_conn

router = APIRouter(prefix="/ingest", tags=["ingest"])


class IngestRunResponse(BaseModel):
    run_id: int
    league_id: str
    status: str


class IngestStatusResponse(BaseModel):
    league_id: str
    last_run_status: str | None
    last_run_at: str | None
    gap_count: int
    gaps: list[dict[str, Any]]


class AdpBaselineRefreshResponse(BaseModel):
    source: str
    source_rows: int
    matched_rows: int
    matched_unique_rows: int
    unmatched_rows: int
    num_qbs: int
    num_teams: int
    ppr: float


class TeamContextRefreshResponse(BaseModel):
    season: int
    environment_rows: int
    upserted_rows: int


class DraftCapitalRefreshSummary(BaseModel):
    draft_year: int
    source_rows: int
    matched_rows: int
    updated_rows: int
    unmatched_rows: int
    rebuilt_boards: int


class LeagueArtifactRefreshSummary(BaseModel):
    league_id: str
    roster_count: int
    player_value_count: int
    manager_profile_count: int
    snapshot_count: int


class LeagueRefreshPipelineResponse(BaseModel):
    league_id: str
    run_id: int
    run_type: str
    sleeper_status: str
    adp: AdpBaselineRefreshResponse
    draft_capital: DraftCapitalRefreshSummary
    artifacts: LeagueArtifactRefreshSummary


def _resolve_adp_refresh_profile(
    conn: duckdb.DuckDBPyConnection,
    *,
    league_id: str | None,
    num_qbs: int | None,
    num_teams: int | None,
    ppr: float | None,
) -> tuple[int, int, float]:
    resolved_num_qbs = num_qbs
    resolved_num_teams = num_teams
    resolved_ppr = ppr

    target_league_id = league_id
    if target_league_id is None:
        first_league = conn.execute(
            """
            SELECT league_id
            FROM leagues
            ORDER BY league_id
            LIMIT 1
            """
        ).fetchone()
        target_league_id = str(first_league[0]) if first_league else None

    if target_league_id is not None:
        league_row = conn.execute(
            """
            SELECT superflex, ppr
            FROM leagues
            WHERE league_id = ?
            LIMIT 1
            """,
            [target_league_id],
        ).fetchone()
        if league_row is None and league_id is not None:
            raise HTTPException(status_code=404, detail=f"League {league_id} not found.")
        if league_row is not None:
            if resolved_num_qbs is None:
                resolved_num_qbs = 2 if bool(league_row[0]) else 1
            if resolved_ppr is None and league_row[1] is not None:
                resolved_ppr = float(league_row[1])
            if resolved_num_teams is None:
                roster_row = conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM rosters
                    WHERE league_id = ?
                    """,
                    [target_league_id],
                ).fetchone()
                if roster_row and roster_row[0]:
                    resolved_num_teams = int(roster_row[0])

    resolved_num_qbs = resolved_num_qbs if resolved_num_qbs is not None else 1
    resolved_num_teams = resolved_num_teams if resolved_num_teams is not None else 12
    resolved_ppr = resolved_ppr if resolved_ppr is not None else 1.0

    return resolved_num_qbs, resolved_num_teams, resolved_ppr


@router.post("/team-context/refresh", response_model=TeamContextRefreshResponse)
def refresh_team_context(
    season: int = Query(default=2026, ge=1999, le=2035),
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> TeamContextRefreshResponse:
    summary = TeamContextRefreshService(conn).refresh(season)
    return TeamContextRefreshResponse(
        season=summary.season,
        environment_rows=summary.environment_rows,
        upserted_rows=summary.upserted_rows,
    )


@router.post("/{league_id}", response_model=IngestRunResponse)
async def trigger_ingest(
    league_id: str,
    run_type: str = Query(default="full", pattern="^(full|incremental)$"),
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> IngestRunResponse:
    try:
        async with SleeperClient() as client:
            service = IngestService(conn, client)
            run_id = await service.run(league_id, run_type)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail={"detail": "ingest_in_progress", "league_id": league_id},
        ) from exc

    row = conn.execute("SELECT status FROM ingest_runs WHERE id = ?", [run_id]).fetchone()
    status = row[0] if row else "complete"
    return IngestRunResponse(run_id=run_id, league_id=league_id, status=status)


@router.post("/{league_id}/refresh-pipeline", response_model=LeagueRefreshPipelineResponse)
async def refresh_league_pipeline(
    league_id: str,
    run_type: str = Query(default="incremental", pattern="^(full|incremental)$"),
    draft_year: int = Query(default=2026, ge=2020, le=2035),
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> LeagueRefreshPipelineResponse:
    try:
        async with SleeperClient() as client:
            service = IngestService(conn, client)
            run_id = await service.run(league_id, run_type)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail={"detail": "ingest_in_progress", "league_id": league_id},
        ) from exc

    row = conn.execute("SELECT status FROM ingest_runs WHERE id = ?", [run_id]).fetchone()
    sleeper_status = row[0] if row else "complete"

    resolved_num_qbs, resolved_num_teams, resolved_ppr = _resolve_adp_refresh_profile(
        conn,
        league_id=league_id,
        num_qbs=None,
        num_teams=None,
        ppr=None,
    )
    try:
        adp_summary = await refresh_adp_baseline_from_fantasycalc(
            conn,
            num_qbs=resolved_num_qbs,
            num_teams=resolved_num_teams,
            ppr=resolved_ppr,
        )
    except FantasyCalcUnavailableError as exc:
        raise HTTPException(status_code=503, detail="FantasyCalc ADP API unavailable.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    draft_capital_summary = refresh_actual_draft_capital(conn, draft_year=draft_year)
    artifact_summary = refresh_league_artifacts(conn, league_id)

    return LeagueRefreshPipelineResponse(
        league_id=league_id,
        run_id=run_id,
        run_type=run_type,
        sleeper_status=sleeper_status,
        adp=AdpBaselineRefreshResponse(
            source="fantasycalc_api",
            source_rows=adp_summary["source_rows"],
            matched_rows=adp_summary["matched_rows"],
            matched_unique_rows=adp_summary["matched_unique_rows"],
            unmatched_rows=adp_summary["unmatched_rows"],
            num_qbs=resolved_num_qbs,
            num_teams=resolved_num_teams,
            ppr=resolved_ppr,
        ),
        draft_capital=DraftCapitalRefreshSummary(**draft_capital_summary),
        artifacts=LeagueArtifactRefreshSummary(**artifact_summary),
    )


@router.post("/adp-baseline/refresh", response_model=AdpBaselineRefreshResponse)
async def refresh_adp_baseline(
    league_id: str | None = Query(default=None),
    num_qbs: int | None = Query(default=None, ge=1, le=3),
    num_teams: int | None = Query(default=None, ge=1, le=32),
    ppr: float | None = Query(default=None, ge=0.0, le=2.0),
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> AdpBaselineRefreshResponse:
    resolved_num_qbs, resolved_num_teams, resolved_ppr = _resolve_adp_refresh_profile(
        conn,
        league_id=league_id,
        num_qbs=num_qbs,
        num_teams=num_teams,
        ppr=ppr,
    )

    try:
        refresh_summary = await refresh_adp_baseline_from_fantasycalc(
            conn,
            num_qbs=resolved_num_qbs,
            num_teams=resolved_num_teams,
            ppr=resolved_ppr,
        )
    except FantasyCalcUnavailableError as exc:
        raise HTTPException(status_code=503, detail="FantasyCalc ADP API unavailable.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return AdpBaselineRefreshResponse(
        source="fantasycalc_api",
        source_rows=refresh_summary["source_rows"],
        matched_rows=refresh_summary["matched_rows"],
        matched_unique_rows=refresh_summary["matched_unique_rows"],
        unmatched_rows=refresh_summary["unmatched_rows"],
        num_qbs=resolved_num_qbs,
        num_teams=resolved_num_teams,
        ppr=resolved_ppr,
    )


@router.get("/status/{league_id}", response_model=IngestStatusResponse)
def get_ingest_status(
    league_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> IngestStatusResponse:
    row = conn.execute(
        """
        SELECT status, completed_at, gaps_json
        FROM ingest_runs
        WHERE league_id = ?
        ORDER BY started_at DESC
        LIMIT 1
        """,
        [league_id],
    ).fetchone()

    if row is None:
        return IngestStatusResponse(
            league_id=league_id,
            last_run_status=None,
            last_run_at=None,
            gap_count=0,
            gaps=[],
        )

    try:
        gaps = json.loads(row[2]) if row[2] else []
    except json.JSONDecodeError:
        gaps = []

    return IngestStatusResponse(
        league_id=league_id,
        last_run_status=row[0],
        last_run_at=row[1].isoformat() if row[1] else None,
        gap_count=len(gaps),
        gaps=gaps,
    )
