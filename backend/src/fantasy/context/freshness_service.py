from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable

from fantasy.context.constants import FRESHNESS_THRESHOLDS
from fantasy.context.context_repo import ContextRepo
from fantasy.context.models import FreshnessTag

ClockFn = Callable[[], datetime]


class FreshnessService:
    def __init__(
        self,
        repo: ContextRepo,
        now: ClockFn = lambda: datetime.now(tz=timezone.utc),
    ) -> None:
        self._repo = repo
        self._now = now

    def get_tags(self, league_id: str, domains: list[str]) -> list[FreshnessTag]:
        rows = self._repo.get_freshness_rows(league_id, domains)
        now = self._now()
        tags: list[FreshnessTag] = []
        for domain in domains:
            row = rows.get(domain)
            threshold_hours = FRESHNESS_THRESHOLDS.get(domain, 48)
            if row is None or row.last_updated is None:
                tags.append(
                    FreshnessTag(
                        domain=domain,
                        last_updated=None,
                        is_stale=True,
                        warning=(
                            f"{domain.replace('_', ' ').title()} data has never been "
                            "updated - verify before acting"
                        ),
                    )
                )
                continue
            age = now - row.last_updated.replace(tzinfo=timezone.utc)
            is_stale = age > timedelta(hours=threshold_hours)
            warning = (
                f"{domain.replace('_', ' ').title()} data is "
                f"{int(age.total_seconds() / 3600)}h old"
                if is_stale
                else None
            )
            tags.append(
                FreshnessTag(
                    domain=domain,
                    last_updated=row.last_updated,
                    is_stale=is_stale,
                    warning=warning,
                )
            )
        return tags

    def mark_refreshed(
        self,
        league_id: str,
        domain: str,
        notes: str | None = None,
    ) -> FreshnessTag:
        now = self._now()
        self._repo.upsert_freshness(league_id, domain, now, notes)
        return FreshnessTag(
            domain=domain,
            last_updated=now,
            is_stale=False,
            warning=None,
        )

