from __future__ import annotations

from datetime import datetime, timezone

import duckdb
from fastapi import APIRouter, Depends

from fantasy.routers.deps import get_read_db_conn
from fantasy.trends.models import OpportunityFeedResponse
from fantasy.trends.opportunity_engine import OpportunityEngine

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@router.get("", response_model=OpportunityFeedResponse)
def get_opportunity_feed(
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> OpportunityFeedResponse:
    items = OpportunityEngine(conn).build_feed()
    return OpportunityFeedResponse(
        items=items,
        total=len(items),
        computed_at=datetime.now(timezone.utc).isoformat(),
    )
