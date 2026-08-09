from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import json
import re
import socket
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

from fantasy.config import REPO_ROOT, Settings, get_settings

MAX_BODY_BYTES = 2_000_000
MAX_TEXT_CHARS = 24_000
MAX_REDIRECTS = 5


class PublicSourceUnavailable(RuntimeError):
    pass


class PublicSourceBlocked(PublicSourceUnavailable):
    pass


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() in {"script", "style", "noscript", "svg"}:
            self._ignored += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() in {"script", "style", "noscript", "svg"} and self._ignored:
            self._ignored -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored:
            text = re.sub(r"\s+", " ", data).strip()
            if text:
                self.parts.append(text)


def sanitize_html(body: str, *, limit: int = MAX_TEXT_CHARS) -> str:
    parser = _TextExtractor()
    parser.feed(body)
    return "\n".join(parser.parts)[:limit]


def _validate_ip(address: str) -> None:
    ip = ipaddress.ip_address(address)
    if not ip.is_global:
        raise PublicSourceBlocked(f"non-public address is not allowed: {ip}")


async def validate_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise PublicSourceBlocked("only public http and https URLs are allowed")
    if not parsed.hostname or parsed.username or parsed.password:
        raise PublicSourceBlocked("URL must have a public hostname and no embedded credentials")
    host = parsed.hostname.casefold().rstrip(".")
    if host == "localhost" or host.endswith(".local"):
        raise PublicSourceBlocked("local hostnames are not allowed")
    try:
        _validate_ip(host)
        return
    except ValueError:
        pass
    loop = asyncio.get_running_loop()
    try:
        infos = await loop.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise PublicSourceUnavailable(f"DNS resolution failed for {host}") from exc
    addresses = {str(info[4][0]) for info in infos}
    if not addresses:
        raise PublicSourceUnavailable(f"DNS returned no addresses for {host}")
    for address in addresses:
        _validate_ip(address)


@dataclass(frozen=True)
class PublicDocument:
    url: str
    text: str
    content_hash: str
    fetched_at: datetime
    retrieval: str
    raw_cache_path: Path


class PublicPageFetcher:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._cache = REPO_ROOT / "data" / "cache" / "intelligence"
        self._last_request_at = 0.0

    async def _throttle(self) -> None:
        interval = max(0.0, self._settings.INTELLIGENCE_MIN_REQUEST_INTERVAL_SECONDS)
        remaining = interval - (time.monotonic() - self._last_request_at)
        if remaining > 0:
            await asyncio.sleep(remaining)
        self._last_request_at = time.monotonic()

    async def fetch(self, url: str, *, allow_browser: bool = True) -> PublicDocument:
        await validate_public_url(url)
        await self._respect_robots(url)
        try:
            return await self._fetch_http(url)
        except PublicSourceBlocked:
            raise
        except PublicSourceUnavailable:
            if not (allow_browser and self._settings.INTELLIGENCE_BROWSER_ENABLED):
                raise
        return await self._fetch_browser(url)

    async def _respect_robots(self, url: str) -> None:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        await validate_public_url(robots_url)
        try:
            async with httpx.AsyncClient(timeout=8, follow_redirects=False) as client:
                await self._throttle()
                response = await client.get(
                    robots_url,
                    headers={"User-Agent": self._settings.INTELLIGENCE_USER_AGENT},
                )
        except httpx.HTTPError:
            return
        if response.status_code >= 400:
            return
        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(response.text.splitlines())
        if not parser.can_fetch(self._settings.INTELLIGENCE_USER_AGENT, url):
            raise PublicSourceBlocked("robots.txt disallows this URL")

    async def _fetch_http(self, url: str) -> PublicDocument:
        current = url
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
            for _ in range(MAX_REDIRECTS + 1):
                await validate_public_url(current)
                try:
                    await self._throttle()
                    response = await client.get(
                        current,
                        headers={"User-Agent": self._settings.INTELLIGENCE_USER_AGENT},
                    )
                except httpx.HTTPError as exc:
                    raise PublicSourceUnavailable(str(exc)) from exc
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        raise PublicSourceUnavailable("redirect omitted Location header")
                    current = urljoin(current, location)
                    continue
                if response.status_code in {401, 403, 407, 429}:
                    raise PublicSourceBlocked(f"source returned HTTP {response.status_code}")
                if response.status_code >= 400:
                    raise PublicSourceUnavailable(f"source returned HTTP {response.status_code}")
                content = response.content
                if len(content) > MAX_BODY_BYTES:
                    raise PublicSourceUnavailable("response exceeded the bounded body limit")
                body = content.decode(response.encoding or "utf-8", errors="replace")
                text = sanitize_html(body)
                if len(text) < 80:
                    raise PublicSourceUnavailable("HTTP response contained no usable public content")
                return self._document(current, body, text, "http")
        raise PublicSourceUnavailable("too many redirects")

    async def _fetch_browser(self, url: str) -> PublicDocument:
        await validate_public_url(url)
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise PublicSourceUnavailable(
                "browser fallback is enabled but Python Playwright is not installed"
            ) from exc
        async with async_playwright() as playwright:
            configured_executable = self._settings.INTELLIGENCE_BROWSER_EXECUTABLE_PATH
            default_chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
            executable_path = configured_executable or (
                str(default_chrome) if default_chrome.exists() else None
            )
            browser = await playwright.chromium.launch(
                headless=True, executable_path=executable_path
            )
            try:
                context = await browser.new_context(
                    user_agent=self._settings.INTELLIGENCE_USER_AGENT
                )
                page = await context.new_page()

                async def guard(route: object) -> None:
                    request_url = route.request.url  # type: ignore[attr-defined]
                    try:
                        await validate_public_url(request_url)
                    except PublicSourceUnavailable:
                        await route.abort()  # type: ignore[attr-defined]
                        return
                    await route.continue_()  # type: ignore[attr-defined]

                await page.route("**/*", guard)
                response = await page.goto(url, wait_until="domcontentloaded", timeout=20_000)
                if response is None or response.status in {401, 403, 407, 429}:
                    raise PublicSourceBlocked("browser source was blocked or unavailable")
                final_url = page.url
                await validate_public_url(final_url)
                body = await page.content()
                text = sanitize_html(body)
                if len(text) < 80:
                    raise PublicSourceUnavailable("browser rendered no usable public content")
                return self._document(final_url, body, text, "browser")
            finally:
                await browser.close()

    def _document(self, url: str, body: str, text: str, retrieval: str) -> PublicDocument:
        digest = hashlib.sha256(body.encode()).hexdigest()
        self._cache.mkdir(parents=True, exist_ok=True)
        self.prune_cache()
        path = self._cache / f"{digest}.json"
        if not path.exists():
            path.write_text(json.dumps({"url": url, "body": body}), encoding="utf-8")
        return PublicDocument(
            url=url,
            text=text[:MAX_TEXT_CHARS],
            content_hash=digest,
            fetched_at=datetime.now(timezone.utc),
            retrieval=retrieval,
            raw_cache_path=path,
        )

    def prune_cache(self) -> None:
        if not self._cache.exists():
            return
        cutoff = datetime.now(timezone.utc) - timedelta(days=self._settings.INTELLIGENCE_CACHE_DAYS)
        for item in self._cache.glob("*.json"):
            modified = datetime.fromtimestamp(item.stat().st_mtime, tz=timezone.utc)
            if modified < cutoff:
                item.unlink(missing_ok=True)


__all__ = [
    "PublicDocument",
    "PublicPageFetcher",
    "PublicSourceBlocked",
    "PublicSourceUnavailable",
    "sanitize_html",
    "validate_public_url",
]
