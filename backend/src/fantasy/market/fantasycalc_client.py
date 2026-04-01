from __future__ import annotations

from typing import Any

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from fantasy.market.models import ExternalPlayerValue, FantasyCalcUnavailableError


def _is_retriable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (429, 500, 502, 503, 504)
    return isinstance(exc, httpx.NetworkError)


class FantasyCalcClient:
    BASE_URL = "https://api.fantasycalc.com"

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "FantasyCalcClient":
        self._client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception(_is_retriable),
        reraise=True,
    )
    async def _get(self, path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        if self._client is None:
            raise RuntimeError("FantasyCalcClient must be used as an async context manager.")
        response = await self._client.get(f"{self.BASE_URL}{path}", params=params)
        response.raise_for_status()
        payload = response.json()
        return list(payload or [])

    async def fetch_dynasty_values(
        self,
        num_qbs: int,
        num_teams: int,
        ppr: float,
    ) -> list[ExternalPlayerValue]:
        try:
            rows = await self._get(
                "/values/current",
                {
                    "isDynasty": "true",
                    "numQbs": num_qbs,
                    "numTeams": num_teams,
                    "ppr": ppr,
                },
            )
        except Exception as exc:  # pragma: no cover - network path
            raise FantasyCalcUnavailableError(str(exc)) from exc

        values: list[ExternalPlayerValue] = []
        for row in rows:
            player = dict(row.get("player") or {})
            value = row.get("value")
            rank = row.get("overallRank")
            if value is None or rank is None:
                continue
            values.append(
                ExternalPlayerValue(
                    mfl_id=str(player.get("mflId")) if player.get("mflId") is not None else None,
                    player_name=str(player.get("name") or "Unknown Player"),
                    position=str(player.get("position")) if player.get("position") is not None else None,
                    team=str(player.get("maybeTeam")) if player.get("maybeTeam") is not None else None,
                    dynasty_value=float(value),
                    overall_rank=int(rank),
                    trend_30day=(
                        float(row.get("trend30Day"))
                        if row.get("trend30Day") is not None
                        else None
                    ),
                )
            )
        return values


__all__ = ["FantasyCalcClient"]
