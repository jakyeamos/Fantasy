from __future__ import annotations

from datetime import date

import duckdb
from fastapi import APIRouter, Depends, HTTPException, status

from fantasy.intelligence.brief_builder import MorningBriefBuilder
from fantasy.intelligence.event_store import IntelligenceStore
from fantasy.intelligence.fresh_models import (
    AnalyzeUrlRequest,
    AnalyzeUrlResponse,
    BriefFeedbackRequest,
    EventDetail,
    EventReviewRequest,
    FootballEvent,
    IntelligenceRunResult,
    MorningBrief,
    RefreshRequest,
)
from fantasy.intelligence.impact_engine import LeagueImpactEngine
from fantasy.intelligence.public_sources import PublicSourceBlocked, PublicSourceUnavailable
from fantasy.intelligence.runner import FreshIntelligenceRunner
from fantasy.routers.deps import get_read_db_conn, get_write_db_conn

router = APIRouter(prefix="/v2", tags=["fresh-intelligence"])


@router.post("/intelligence/refresh", response_model=IntelligenceRunResult)
async def refresh_intelligence(
    request: RefreshRequest,
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> IntelligenceRunResult:
    return await FreshIntelligenceRunner(conn).run(
        scheduled=request.scheduled,
        source_ids=request.source_ids,
        league_ids=request.league_ids,
    )


@router.post("/intelligence/analyze-url", response_model=AnalyzeUrlResponse)
async def analyze_public_url(
    request: AnalyzeUrlRequest,
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> AnalyzeUrlResponse:
    try:
        return await FreshIntelligenceRunner(conn).analyze_url(str(request.url))
    except PublicSourceBlocked as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except PublicSourceUnavailable as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/briefs/today", response_model=MorningBrief)
def get_today_brief(
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> MorningBrief:
    try:
        return IntelligenceStore(conn).get_brief(date.today())
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "brief_not_run", "message": "Today's briefing has not been run."},
        ) from exc


@router.get("/events/{event_id}", response_model=EventDetail)
def get_event_detail(
    event_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> EventDetail:
    store = IntelligenceStore(conn)
    try:
        event = store.get_event(event_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found") from exc
    observations = [store.get_observation(item) for item in event.observation_ids]
    return EventDetail(event=event, observations=observations, impacts=store.list_impacts(event_id))


@router.get("/intelligence/review", response_model=list[FootballEvent])
def get_review_queue(
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> list[FootballEvent]:
    from fantasy.intelligence.fresh_models import VerificationState

    return IntelligenceStore(conn).list_events(states=[
        VerificationState.WATCH,
        VerificationState.CONFLICTED,
        VerificationState.MANUAL_REVIEW,
    ])


@router.post("/events/{event_id}/review", response_model=EventDetail)
def review_event(
    event_id: str,
    request: EventReviewRequest,
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> EventDetail:
    store = IntelligenceStore(conn)
    try:
        event = store.review_event(event_id, request.decision, request.notes)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found") from exc
    impacts = LeagueImpactEngine(conn).compute(event)
    store.replace_impacts(event_id, impacts)
    try:
        current = store.get_brief(date.today())
    except KeyError:
        pass
    else:
        store.publish_brief(
            run_id=current.run_id,
            status=current.status,
            items=MorningBriefBuilder(store).build(),
            outcomes=current.source_health,
        )
    observations = [store.get_observation(item) for item in event.observation_ids]
    return EventDetail(event=event, observations=observations, impacts=impacts)


@router.post("/briefs/{brief_id}/items/{item_id}/feedback", status_code=201)
def record_brief_feedback(
    brief_id: str,
    item_id: str,
    request: BriefFeedbackRequest,
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> dict[str, str]:
    row = conn.execute(
        "SELECT 1 FROM daily_brief_items WHERE brief_id = ? AND item_id = ?",
        [brief_id, item_id],
    ).fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brief item not found")
    feedback_id = IntelligenceStore(conn).save_feedback(
        brief_id, item_id, request.verdict, request.notes
    )
    return {"feedback_id": feedback_id}
