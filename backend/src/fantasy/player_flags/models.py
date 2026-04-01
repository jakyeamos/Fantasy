from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


FlagType = Literal[
    "injury_recovery",
    "depth_chart_competition",
    "role_expansion",
    "role_compression",
    "team_change",
    "age_cliff_proximity",
]


class PlayerContextFlag(BaseModel):
    model_config = ConfigDict(frozen=False)

    player_id: str
    flag_type: FlagType
    created_at: str | None = None
    expires_at: str | None = None
    source: str = "sleeper_ingest"
    metadata: dict[str, Any] = Field(default_factory=dict)


__all__ = ["FlagType", "PlayerContextFlag"]
