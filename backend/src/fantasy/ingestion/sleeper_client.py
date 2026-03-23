from __future__ import annotations

from typing import Any

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential


def _is_retriable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (429, 500, 502, 503, 504)
    return isinstance(exc, httpx.NetworkError)


class SleeperClient:
    BASE_URL = "https://api.sleeper.app/v1"

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "SleeperClient":
        self._client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception(_is_retriable),
        reraise=True,
    )
    async def _get(self, path: str) -> dict[str, Any] | list[Any]:
        if self._client is None:
            raise RuntimeError("SleeperClient must be used as an async context manager.")

        response = await self._client.get(f"{self.BASE_URL}{path}")
        response.raise_for_status()
        return response.json()

    async def fetch_league(self, league_id: str) -> dict[str, Any]:
        return dict(await self._get(f"/league/{league_id}"))

    async def fetch_rosters(self, league_id: str) -> list[dict[str, Any]]:
        return list(await self._get(f"/league/{league_id}/rosters"))

    async def fetch_users(self, league_id: str) -> list[dict[str, Any]]:
        return list(await self._get(f"/league/{league_id}/users"))

    async def fetch_traded_picks(self, league_id: str) -> list[dict[str, Any]]:
        return list(await self._get(f"/league/{league_id}/traded_picks"))

    async def fetch_transactions(self, league_id: str, week: int) -> list[dict[str, Any]]:
        try:
            result = await self._get(f"/league/{league_id}/transactions/{week}")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return []
            raise

        return list(result or [])

    async def fetch_nfl_state(self) -> dict[str, Any]:
        return dict(await self._get("/state/nfl"))

    async def fetch_drafts(self, league_id: str) -> list[dict[str, Any]]:
        try:
            result = await self._get(f"/league/{league_id}/drafts")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return []
            raise
        return list(result or [])

    async def fetch_players(self) -> dict[str, dict[str, Any]]:
        data = await self._get("/players/nfl")
        return dict(data)
