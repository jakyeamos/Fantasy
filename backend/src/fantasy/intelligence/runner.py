from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from urllib.parse import urlparse
from uuid import uuid4

import duckdb

from fantasy.config import get_settings
from fantasy.context.constants import GLOBAL_FRESHNESS_LEAGUE_ID
from fantasy.context.context_repo import ContextRepo
from fantasy.context.freshness_service import FreshnessService
from fantasy.intelligence.brief_builder import MorningBriefBuilder
from fantasy.intelligence.event_store import IntelligenceStore
from fantasy.intelligence.extractor import get_narrative_extractor
from fantasy.intelligence.fresh_models import (
    AnalyzeUrlResponse,
    ExtractedEventClaim,
    IntelligenceRunResult,
    ParseStatus,
    SourceObservation,
    SourceOutcome,
    SourceTier,
)
from fantasy.intelligence.impact_engine import LeagueImpactEngine
from fantasy.intelligence.public_sources import (
    PublicPageFetcher,
    PublicSourceBlocked,
    PublicSourceUnavailable,
)
from fantasy.intelligence.sources import LocalLeagueSource, NflreadpySource, SourceBatch


def _official_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").casefold()
    return host == "nfl.com" or host.endswith(".nfl.com")


class FreshIntelligenceRunner:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn
        self._store = IntelligenceStore(conn)
        self._freshness = FreshnessService(ContextRepo(conn))

    async def run(
        self,
        *,
        scheduled: bool = False,
        source_ids: list[str] | None = None,
        league_ids: list[str] | None = None,
    ) -> IntelligenceRunResult:
        trigger = "scheduled" if scheduled else "on_demand"
        run_id = self._store.start_run(trigger)
        outcomes: list[SourceOutcome] = []
        event_ids: set[str] = set()
        impact_count = 0
        brief_id: str | None = None
        try:
            season = self._active_season()
            allowed = set(source_ids) if source_ids else None
            batches = NflreadpySource(self._conn, run_id, season).collect(allowed)
            batches.extend(LocalLeagueSource(self._conn, run_id).collect(allowed))
            batches.extend(await self._configured_public_batches(run_id, allowed))
            for batch in batches:
                if batch.outcome is None:
                    continue
                fetched_at = max(
                    (item.fetched_at for item in batch.observations), default=None
                )
                batch.outcome = batch.outcome.model_copy(update={
                    "fetched_at": fetched_at,
                    "coverage_through": batch.coverage_through,
                })
            outcomes = [batch.outcome for batch in batches if batch.outcome is not None]
            target_leagues = league_ids or self._league_ids()
            self._record_domain_freshness(batches, target_leagues)
            for batch in batches:
                for observation in batch.observations:
                    stored_observation = self._store.save_observation(observation)
                    # Retarget claims to the immutable cached observation on hash hits.
                    for original, claim in batch.claims:
                        if original.observation_id != observation.observation_id:
                            continue
                        resolved = self._resolve_claim(claim)
                        event = self._store.upsert_claim(stored_observation, resolved)
                        event_ids.add(event.event_id)
            engine = LeagueImpactEngine(self._conn)
            for event_id in sorted(event_ids):
                event = self._store.get_event(event_id)
                impacts = engine.compute(event)
                self._store.replace_impacts(event_id, impacts)
                impact_count += len(impacts)
            items = MorningBriefBuilder(self._store).build()
            degraded = any(outcome.status in {"partial", "failed"} for outcome in outcomes)
            brief = self._store.publish_brief(
                run_id=run_id,
                status="degraded" if degraded else ("ready" if items else "empty"),
                items=items,
                outcomes=outcomes,
            )
            brief_id = brief.brief_id
            status = "degraded" if degraded else "complete"
            self._store.finish_run(run_id, status=status, outcomes=outcomes,
                event_count=len(event_ids), impact_count=impact_count, brief_id=brief_id)
            return IntelligenceRunResult(
                run_id=run_id, status=status, source_outcomes=outcomes,
                event_count=len(event_ids), impact_count=impact_count, brief_id=brief_id,
            )
        except Exception as exc:
            self._store.finish_run(run_id, status="failed", outcomes=outcomes,
                event_count=len(event_ids), impact_count=impact_count, brief_id=brief_id,
                error_message=f"{type(exc).__name__}: {exc}")
            raise

    async def analyze_url(self, url: str) -> AnalyzeUrlResponse:
        run_id = self._store.start_run("manual_url")
        outcome: SourceOutcome
        try:
            document = await PublicPageFetcher().fetch(url)
            source_id = f"manual:{urlparse(document.url).hostname or 'public'}"
            cached = self._store.find_observation(source_id, document.content_hash)
            if cached is not None:
                events = self._store.list_events_for_observation(cached.observation_id)
                impacts = [
                    impact
                    for event in events
                    for impact in self._store.list_impacts(event.event_id)
                ]
                outcome = SourceOutcome(
                    source_id=source_id,
                    status="complete",
                    records_seen=len(events),
                    fetched_at=document.fetched_at,
                    coverage_through=cached.coverage_through,
                    message="Unchanged content; reused cached extraction.",
                )
                items = MorningBriefBuilder(self._store).build()
                brief = self._store.publish_brief(
                    run_id=run_id,
                    status="ready" if items else "empty",
                    items=items,
                    outcomes=[outcome],
                )
                self._store.finish_run(
                    run_id,
                    status="complete",
                    outcomes=[outcome],
                    event_count=len(events),
                    impact_count=len(impacts),
                    brief_id=brief.brief_id,
                )
                return AnalyzeUrlResponse(
                    run_id=run_id,
                    url=document.url,
                    retrieval=document.retrieval,
                    events=events,
                    impacts=impacts,
                )
            extractor = get_narrative_extractor()
            claims = await extractor.extract(document.text, source_url=document.url)
            official = _official_url(document.url)
            observation = SourceObservation(
                observation_id=str(uuid4()), run_id=run_id, source_id=source_id,
                source_tier=SourceTier.OFFICIAL if official else (
                    SourceTier.BROWSER if document.retrieval == "browser" else SourceTier.PUBLIC
                ),
                url=document.url, fetched_at=document.fetched_at, observed_at=document.fetched_at,
                content_hash=document.content_hash,
                parse_status=ParseStatus.PARSED if claims else ParseStatus.MANUAL_REVIEW,
                evidence_excerpt=document.text[:500],
                payload={"text_length": len(document.text), "claim_count": len(claims)},
                authoritative=official, model_extracted=(
                    get_settings().INTELLIGENCE_EXTRACTOR_PROVIDER != "none"
                ),
            )
            stored = self._store.save_observation(observation)
            events = [
                self._store.upsert_claim(stored, self._resolve_claim(claim)) for claim in claims
            ]
            impacts = []
            engine = LeagueImpactEngine(self._conn)
            for event in events:
                computed = engine.compute(event)
                self._store.replace_impacts(event.event_id, computed)
                impacts.extend(computed)
            outcome = SourceOutcome(source_id=source_id, status="complete",
                records_seen=len(claims), observations_written=1, events_written=len(events),
                fetched_at=document.fetched_at, coverage_through=document.fetched_at,
                message=None if claims else "No schema-valid event claim; queued as unavailable evidence")
            items = MorningBriefBuilder(self._store).build()
            brief = self._store.publish_brief(run_id=run_id, status="ready" if items else "empty",
                items=items, outcomes=[outcome])
            self._store.finish_run(run_id, status="complete", outcomes=[outcome],
                event_count=len(events), impact_count=len(impacts), brief_id=brief.brief_id)
            return AnalyzeUrlResponse(run_id=run_id, url=document.url,
                retrieval=document.retrieval, events=events, impacts=impacts)
        except (PublicSourceBlocked, PublicSourceUnavailable) as exc:
            outcome = SourceOutcome(source_id=f"manual:{urlparse(url).hostname or 'public'}",
                status="failed", message=str(exc))
            self._store.finish_run(run_id, status="failed", outcomes=[outcome],
                event_count=0, impact_count=0, brief_id=None, error_message=str(exc))
            raise

    async def _configured_public_batches(
        self, run_id: str, source_ids: set[str] | None = None
    ) -> list[SourceBatch]:
        urls = [url.strip() for url in get_settings().INTELLIGENCE_PUBLIC_FEEDS.split(",") if url.strip()]
        batches: list[SourceBatch] = []
        fetcher = PublicPageFetcher()
        for index, url in enumerate(urls):
            source_id = f"public:{index}:{urlparse(url).hostname or 'source'}"
            if source_ids is not None and source_id not in source_ids:
                continue
            try:
                document = await fetcher.fetch(url)
                cached = self._store.find_observation(source_id, document.content_hash)
                if cached is not None:
                    claim_count = int(cached.payload.get("claim_count", 0))
                    batches.append(SourceBatch(
                        source_id=source_id,
                        domain="public_news",
                        observations=[cached],
                        outcome=SourceOutcome(
                            source_id=source_id,
                            status="complete",
                            records_seen=claim_count,
                            message="Unchanged content; reused cached extraction.",
                        ),
                        authoritative_empty=cached.authoritative and claim_count == 0,
                        coverage_through=document.fetched_at,
                    ))
                    continue
                claims = await get_narrative_extractor().extract(document.text, source_url=document.url)
                official = _official_url(document.url)
                observation = SourceObservation(
                    observation_id=str(uuid4()), run_id=run_id, source_id=source_id,
                    source_tier=SourceTier.OFFICIAL if official else (
                        SourceTier.BROWSER if document.retrieval == "browser" else SourceTier.PUBLIC
                    ), url=document.url, fetched_at=document.fetched_at,
                    observed_at=document.fetched_at, coverage_through=document.fetched_at,
                    content_hash=document.content_hash,
                    parse_status=ParseStatus.PARSED if claims else ParseStatus.EMPTY,
                    evidence_excerpt=document.text[:500],
                    payload={"text_length": len(document.text), "claim_count": len(claims)},
                    authoritative=official,
                    model_extracted=get_settings().INTELLIGENCE_EXTRACTOR_PROVIDER != "none",
                )
                batches.append(SourceBatch(source_id=source_id, domain="public_news",
                    observations=[observation], claims=[(observation, claim) for claim in claims],
                    outcome=SourceOutcome(source_id=source_id, status="complete",
                        records_seen=len(claims), observations_written=1, events_written=len(claims)),
                    authoritative_empty=official and not claims,
                    coverage_through=document.fetched_at))
            except (PublicSourceBlocked, PublicSourceUnavailable) as exc:
                now = datetime.now(timezone.utc)
                observation = SourceObservation(
                    observation_id=str(uuid4()), run_id=run_id, source_id=source_id,
                    source_tier=SourceTier.PUBLIC, url=url, fetched_at=now,
                    content_hash=hashlib.sha256(f"{url}:{now.isoformat()}:{exc}".encode()).hexdigest(),
                    parse_status=ParseStatus.BLOCKED if isinstance(exc, PublicSourceBlocked) else ParseStatus.UNAVAILABLE,
                    evidence_excerpt=str(exc), payload={"error": str(exc)},
                )
                batches.append(SourceBatch(source_id=source_id, domain="public_news",
                    observations=[observation], outcome=SourceOutcome(source_id=source_id,
                        status="failed", message=str(exc))))
        return batches

    def _resolve_claim(self, claim: ExtractedEventClaim) -> ExtractedEventClaim:
        if claim.player_id or not claim.player_name:
            return claim
        rows = self._conn.execute(
            "SELECT player_id, team FROM players WHERE lower(full_name) = lower(?)",
            [claim.player_name],
        ).fetchall()
        if len(rows) != 1:
            return claim
        return claim.model_copy(update={"player_id": str(rows[0][0]),
            "team": claim.team or (str(rows[0][1]) if rows[0][1] else None)})

    def _record_domain_freshness(self, batches: list[SourceBatch], league_ids: list[str]) -> None:
        grouped: dict[str, list[SourceBatch]] = {}
        for batch in batches:
            grouped.setdefault(batch.domain, []).append(batch)
        for domain, domain_batches in grouped.items():
            successful = [batch for batch in domain_batches if batch.outcome and batch.outcome.status == "complete" and batch.outcome.records_seen > 0]
            all_empty_authoritative = bool(domain_batches) and all(
                batch.outcome is not None and batch.outcome.status == "complete" and batch.authoritative_empty
                for batch in domain_batches
            )
            record_count = sum(batch.outcome.records_seen for batch in domain_batches if batch.outcome)
            parsed = bool(successful) or all_empty_authoritative
            coverage = max((batch.coverage_through for batch in domain_batches if batch.coverage_through), default=None)
            targets = [GLOBAL_FRESHNESS_LEAGUE_ID] if domain in {"player_metadata", "public_news"} else league_ids
            for league_id in targets:
                self._freshness.mark_source_result(
                    league_id=league_id, domain=domain,
                    source_id=",".join(batch.source_id for batch in domain_batches),
                    parsed_successfully=parsed, record_count=record_count,
                    authoritative_empty=all_empty_authoritative,
                    coverage_through=coverage,
                    notes="; ".join(
                        f"{batch.source_id}: {batch.outcome.status if batch.outcome else 'unknown'}"
                        for batch in domain_batches
                    ),
                )

    def _active_season(self) -> int:
        row = self._conn.execute("SELECT MAX(TRY_CAST(season AS INTEGER)) FROM leagues").fetchone()
        return int(row[0]) if row and row[0] else datetime.now(timezone.utc).year

    def _league_ids(self) -> list[str]:
        return [str(row[0]) for row in self._conn.execute("SELECT league_id FROM leagues ORDER BY league_id").fetchall()]


__all__ = ["FreshIntelligenceRunner"]
