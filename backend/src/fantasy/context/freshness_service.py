from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable

from fantasy.context.constants import FRESHNESS_THRESHOLDS, GLOBAL_FRESHNESS_LEAGUE_ID
from fantasy.context.context_repo import ContextRepo
from fantasy.context.models import EvidenceFreshness, FreshnessTag

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
        missing_domains = [domain for domain in domains if domain not in rows]
        if missing_domains and league_id != GLOBAL_FRESHNESS_LEAGUE_ID:
            global_rows = self._repo.get_freshness_rows(
                GLOBAL_FRESHNESS_LEAGUE_ID,
                missing_domains,
            )
            rows.update(global_rows)
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
            is_degraded = row.status != "fresh"
            is_stale = is_degraded or age > timedelta(hours=threshold_hours)
            if is_degraded:
                warning = (
                    f"{domain.replace('_', ' ').title()} refresh is degraded; "
                    "showing the last confirmed snapshot"
                )
            elif is_stale:
                warning = (
                    f"{domain.replace('_', ' ').title()} data is "
                    f"{int(age.total_seconds() / 3600)}h old"
                )
            else:
                warning = None
            tags.append(
                FreshnessTag(
                    domain=domain,
                    last_updated=row.last_updated,
                    fetched_at=row.fetched_at,
                    observed_at=row.observed_at,
                    effective_at=row.effective_at,
                    coverage_through=row.coverage_through,
                    status=row.status,
                    source_id=row.source_id,
                    record_count=row.record_count,
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
        now = self._now().astimezone(timezone.utc).replace(tzinfo=None)
        self._repo.upsert_freshness(league_id, domain, now, notes)
        return FreshnessTag(
            domain=domain,
            last_updated=now,
            fetched_at=now,
            observed_at=now,
            status="fresh",
            is_stale=False,
            warning=None,
        )

    def mark_source_result(
        self,
        *,
        league_id: str,
        domain: str,
        source_id: str,
        parsed_successfully: bool,
        record_count: int,
        authoritative_empty: bool = False,
        observed_at: datetime | None = None,
        effective_at: datetime | None = None,
        coverage_through: datetime | None = None,
        notes: str | None = None,
    ) -> FreshnessTag:
        now = self._now().astimezone(timezone.utc).replace(tzinfo=None)
        row = self._repo.record_source_result(
            league_id=league_id,
            domain=domain,
            fetched_at=now,
            source_id=source_id,
            parsed_successfully=parsed_successfully,
            record_count=record_count,
            authoritative_empty=authoritative_empty,
            observed_at=observed_at or now,
            effective_at=effective_at,
            coverage_through=coverage_through,
            notes=notes,
        )
        is_stale = row.status != "fresh"
        return FreshnessTag(
            domain=domain,
            last_updated=row.last_updated,
            fetched_at=row.fetched_at,
            observed_at=row.observed_at,
            effective_at=row.effective_at,
            coverage_through=row.coverage_through,
            status=row.status,
            source_id=row.source_id,
            record_count=row.record_count,
            is_stale=is_stale,
            warning=(
                None
                if not is_stale
                else f"{domain.replace('_', ' ').title()} refresh is degraded; showing the last confirmed snapshot"
            ),
        )

    def evidence_freshness(
        self,
        league_id: str,
        domains: list[str],
    ) -> EvidenceFreshness:
        tags = self.get_tags(league_id, domains)
        stale_tags = [tag for tag in tags if tag.is_stale]
        return EvidenceFreshness(
            is_stale=bool(stale_tags),
            stale_domains=[tag.domain for tag in stale_tags],
            warnings=[tag.warning for tag in stale_tags if tag.warning],
        )
