from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class FantasyCalcUnavailableError(Exception):
    """Raised when FantasyCalc is unavailable after retries."""


class ExternalPlayerValue(BaseModel):
    model_config = ConfigDict(frozen=False)

    mfl_id: str | None = None
    player_name: str
    position: str | None = None
    team: str | None = None
    dynasty_value: float
    overall_rank: int
    trend_30day: float | None = None


class LeagueMarketSignal(BaseModel):
    model_config = ConfigDict(frozen=False)

    player_id: str
    league_id: str
    revealed_preference: float
    trade_count: int
    last_updated: str | None = None


__all__ = [
    "ExternalPlayerValue",
    "FantasyCalcUnavailableError",
    "LeagueMarketSignal",
]
