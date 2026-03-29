from __future__ import annotations

from datetime import datetime, timedelta, timezone

import duckdb
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from fantasy.context.calendar_service import CalendarService
from fantasy.context.constants import OVERRIDE_TTL_DAYS
from fantasy.context.context_repo import ContextRepo
from fantasy.context.freshness_service import FreshnessService
from fantasy.context.models import CalendarContext, FreshnessTag
from fantasy.routers.deps import get_read_db_conn, get_write_db_conn

router = APIRouter(prefix="/context", tags=["context"])


class CalendarOverrideRequest(BaseModel):
    state: str
    ttl_days: int | None = None


class FreshnessRefreshRequest(BaseModel):
    domain: str
    notes: str | None = None


@router.get("/{league_id}/calendar", response_model=CalendarContext)
def get_calendar_context(
    league_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> CalendarContext:
    repo = ContextRepo(conn)
    return CalendarService(repo=repo).get_context(league_id)


@router.post("/{league_id}/calendar/override", response_model=CalendarContext)
def set_calendar_override(
    league_id: str,
    body: CalendarOverrideRequest,
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> CalendarContext:
    ttl_days = body.ttl_days if body.ttl_days is not None else OVERRIDE_TTL_DAYS
    expires_at = datetime.now(tz=timezone.utc) + timedelta(days=ttl_days)
    repo = ContextRepo(conn)
    repo.upsert_override(league_id, body.state, expires_at=expires_at, set_by="user")
    return CalendarService(repo=repo).get_context(league_id)


@router.delete("/{league_id}/calendar/override", response_model=CalendarContext)
def clear_calendar_override(
    league_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> CalendarContext:
    repo = ContextRepo(conn)
    repo.clear_override(league_id)
    return CalendarService(repo=repo).get_context(league_id)


@router.get("/{league_id}/freshness", response_model=list[FreshnessTag])
def get_freshness(
    league_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> list[FreshnessTag]:
    repo = ContextRepo(conn)
    domains = [
        "injuries",
        "depth_chart",
        "free_agency",
        "combine",
        "draft_capital",
        "landing_spots",
    ]
    return FreshnessService(repo=repo).get_tags(league_id, domains)


@router.post("/{league_id}/freshness/refresh", response_model=FreshnessTag)
def refresh_freshness(
    league_id: str,
    body: FreshnessRefreshRequest,
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> FreshnessTag:
    repo = ContextRepo(conn)
    return FreshnessService(repo=repo).mark_refreshed(
        league_id,
        body.domain,
        notes=body.notes,
    )
