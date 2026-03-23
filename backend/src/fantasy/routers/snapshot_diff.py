from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends

from fantasy.portfolio.models import DiffRow, SnapshotAnchor
from fantasy.portfolio.snapshot_diff_engine import SnapshotDiffEngine
from fantasy.routers.deps import get_read_db_conn

router = APIRouter(prefix="/leagues", tags=["snapshot-diff"])


@router.get("/{league_id}/snapshot-anchors", response_model=list[SnapshotAnchor])
def get_snapshot_anchors(
    league_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> list[SnapshotAnchor]:
    return SnapshotDiffEngine(conn).load_anchors(league_id)


@router.get("/{league_id}/snapshot-diff", response_model=list[DiffRow])
def get_snapshot_diff(
    league_id: str,
    snapshot_id: int,
    roster_id: int,
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> list[DiffRow]:
    return SnapshotDiffEngine(conn).compute_diff(league_id, snapshot_id, roster_id)
