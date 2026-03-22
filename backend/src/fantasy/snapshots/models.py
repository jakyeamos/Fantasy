from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class SnapshotRecord(BaseModel):
    model_config = ConfigDict(frozen=False)

    id: int
    league_id: str
    snapshot_at: datetime
    snapshot_type: Literal["delta", "full"]
    triggered_by: Literal["ingest", "manual"]
    ingest_run_id: int | None = None
    payload_json: str
    base_snapshot_id: int | None = None


class SnapshotStatus(BaseModel):
    model_config = ConfigDict(frozen=False)

    league_id: str
    last_snapshot_at: datetime | None = None


class SnapshotTriggerResponse(BaseModel):
    model_config = ConfigDict(frozen=False)

    snapshot_ids: list[int]
    count: int
