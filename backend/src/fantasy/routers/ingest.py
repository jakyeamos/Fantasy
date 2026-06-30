from __future__ import annotations

import json
from typing import Any

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from fantasy.context.constants import GLOBAL_FRESHNESS_LEAGUE_ID
from fantasy.context.context_repo import ContextRepo
from fantasy.context.freshness_service import FreshnessService
from fantasy.edge_radar.player_metadata import (
    PlayerMetadataRefreshService,
    import_player_metadata_csv,
)
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
    degradation_warnings: list[str] = Field(default_factory=list)


class IngestStatusResponse(BaseModel):
    league_id: str
    last_run_status: str | None
    last_run_at: str | None
    gap_count: int
    gaps: list[dict[str, Any]]
    degradation_warnings: list[str] = Field(default_factory=list)


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


class PlayerMetadataRefreshResponse(BaseModel):
    season: int
    source_rows: int
    updated_rows: int


class PlayerMetadataImportResponse(BaseModel):
    source_rows: int
    matched_rows: int
    updated_rows: int
    unmatched_rows: int


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
    waiver_recommendation_count: int
    snapshot_count: int


class LeagueRefreshPipelineResponse(BaseModel):
    league_id: str
    run_id: int
    run_type: str
    sleeper_status: str
    adp: AdpBaselineRefreshResponse
    draft_capital: DraftCapitalRefreshSummary
    team_context: TeamContextRefreshResponse
    player_metadata: PlayerMetadataRefreshResponse
    artifacts: LeagueArtifactRefreshSummary
    degradation_warnings: list[str] = Field(default_factory=list)


def _degradation_warnings_from_cursor(cursor_json: str | None) -> list[str]:
    if not cursor_json:
        return []
    try:
        cursor = json.loads(cursor_json)
    except json.JSONDecodeError:
        return []
    warnings = cursor.get("degradation_warnings") if isinstance(cursor, dict) else None
    if not isinstance(warnings, list):
        return []
    return [str(warning) for warning in warnings]


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
    FreshnessService(ContextRepo(conn)).mark_refreshed(
        GLOBAL_FRESHNESS_LEAGUE_ID,
        "team_context",
        f"Team context refreshed for {season}.",
    )
    return TeamContextRefreshResponse(
        season=summary.season,
        environment_rows=summary.environment_rows,
        upserted_rows=summary.upserted_rows,
    )


@router.post("/player-metadata/refresh", response_model=PlayerMetadataRefreshResponse)
def refresh_player_metadata(
    season: int = Query(default=2026, ge=1999, le=2035),
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> PlayerMetadataRefreshResponse:
    summary = PlayerMetadataRefreshService(conn).refresh(season)
    FreshnessService(ContextRepo(conn)).mark_refreshed(
        GLOBAL_FRESHNESS_LEAGUE_ID,
        "player_metadata",
        f"Dense player metadata refreshed for {season}.",
    )
    return PlayerMetadataRefreshResponse(
        season=summary.season,
        source_rows=summary.source_rows,
        updated_rows=summary.updated_rows,
    )


@router.post(
    "/player-metadata/import-csv",
    response_model=PlayerMetadataImportResponse,
)
def import_player_metadata(
    csv_path: str = Query(min_length=1),
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> PlayerMetadataImportResponse:
    summary = import_player_metadata_csv(conn, csv_path)
    FreshnessService(ContextRepo(conn)).mark_refreshed(
        GLOBAL_FRESHNESS_LEAGUE_ID,
        "player_metadata",
        "Dense player metadata imported from CSV.",
    )
    return PlayerMetadataImportResponse(
        source_rows=summary.source_rows,
        matched_rows=summary.matched_rows,
        updated_rows=summary.updated_rows,
        unmatched_rows=summary.unmatched_rows,
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

    row = conn.execute(
        "SELECT status, cursor_json FROM ingest_runs WHERE id = ?",
        [run_id],
    ).fetchone()
    status = row[0] if row else "complete"
    cursor_json = row[1] if row else None
    return IngestRunResponse(
        run_id=run_id,
        league_id=league_id,
        status=status,
        degradation_warnings=_degradation_warnings_from_cursor(cursor_json),
    )


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

    row = conn.execute(
        "SELECT status, cursor_json FROM ingest_runs WHERE id = ?",
        [run_id],
    ).fetchone()
    sleeper_status = row[0] if row else "complete"
    degradation_warnings = _degradation_warnings_from_cursor(row[1] if row else None)

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
    FreshnessService(ContextRepo(conn)).mark_refreshed(
        league_id,
        "market",
        "FantasyCalc ADP baseline refreshed by league refresh pipeline.",
    )

    draft_capital_summary = refresh_actual_draft_capital(conn, draft_year=draft_year)
    team_context_summary = TeamContextRefreshService(conn).refresh(draft_year)
    player_metadata_summary = PlayerMetadataRefreshService(conn).refresh(draft_year)
    freshness = FreshnessService(ContextRepo(conn))
    freshness.mark_refreshed(
        GLOBAL_FRESHNESS_LEAGUE_ID,
        "team_context",
        f"Team context refreshed for {draft_year} by league refresh pipeline.",
    )
    freshness.mark_refreshed(
        GLOBAL_FRESHNESS_LEAGUE_ID,
        "player_metadata",
        f"Dense player metadata refreshed for {draft_year} by league refresh pipeline.",
    )
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
        team_context=TeamContextRefreshResponse(
            season=team_context_summary.season,
            environment_rows=team_context_summary.environment_rows,
            upserted_rows=team_context_summary.upserted_rows,
        ),
        player_metadata=PlayerMetadataRefreshResponse(
            season=player_metadata_summary.season,
            source_rows=player_metadata_summary.source_rows,
            updated_rows=player_metadata_summary.updated_rows,
        ),
        artifacts=LeagueArtifactRefreshSummary(**artifact_summary),
        degradation_warnings=degradation_warnings,
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

    if league_id is not None:
        FreshnessService(ContextRepo(conn)).mark_refreshed(
            league_id,
            "market",
            "FantasyCalc ADP baseline refreshed.",
        )

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
        SELECT status, completed_at, gaps_json, cursor_json
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
            degradation_warnings=[],
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
        degradation_warnings=_degradation_warnings_from_cursor(row[3]),
    )
