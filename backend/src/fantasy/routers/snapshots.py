from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends

from fantasy.routers.deps import get_read_db_conn, get_write_db_conn
from fantasy.snapshots.models import SnapshotStatus, SnapshotTriggerResponse
from fantasy.snapshots.snapshot_service import SnapshotService

router = APIRouter(prefix="/snapshots", tags=["snapshots"])


@router.post("/trigger", response_model=SnapshotTriggerResponse)
def trigger_snapshots(
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> SnapshotTriggerResponse:
    service = SnapshotService(conn)
    snapshot_ids = service.take_snapshot([], triggered_by="manual")
    return SnapshotTriggerResponse(snapshot_ids=snapshot_ids, count=len(snapshot_ids))


@router.get("/status", response_model=list[SnapshotStatus])
def get_snapshot_status(
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> list[SnapshotStatus]:
    rows = conn.execute(
        """
        SELECT l.league_id, MAX(ls.snapshot_at) AS last_snapshot_at
        FROM leagues l
        LEFT JOIN league_snapshots ls ON ls.league_id = l.league_id
        GROUP BY l.league_id
        ORDER BY l.league_id
        """
    ).fetchall()
    return [
        SnapshotStatus(league_id=str(row[0]), last_snapshot_at=row[1]) for row in rows
    ]
