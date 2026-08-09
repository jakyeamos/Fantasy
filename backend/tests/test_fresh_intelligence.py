from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import uuid4

from fantasy.context.context_repo import ContextRepo
from fantasy.context.freshness_service import FreshnessService
from fantasy.intelligence.brief_builder import MorningBriefBuilder
from fantasy.intelligence.event_store import IntelligenceStore
from fantasy.intelligence.fresh_models import (
    EventType,
    ExtractedEventClaim,
    ParseStatus,
    SourceObservation,
    SourceOutcome,
    SourceTier,
    VerificationState,
)
from fantasy.intelligence.impact_engine import LeagueImpactEngine
from fantasy.intelligence.public_sources import PublicDocument
from fantasy.intelligence.runner import FreshIntelligenceRunner
from fantasy.intelligence.sources import SourceBatch
from fantasy.intelligence.sources import LocalLeagueSource


def _observation(
    run_id: str,
    source_id: str,
    *,
    authoritative: bool = False,
    model_extracted: bool = False,
) -> SourceObservation:
    now = datetime.now(timezone.utc)
    return SourceObservation(
        observation_id=str(uuid4()), run_id=run_id, source_id=source_id,
        source_tier=SourceTier.STRUCTURED if authoritative else SourceTier.PUBLIC,
        url=f"https://example.com/{source_id}", fetched_at=now, observed_at=now,
        content_hash=hashlib.sha256(f"{run_id}:{source_id}".encode()).hexdigest(),
        parse_status=ParseStatus.PARSED, evidence_excerpt="Mike Evans was ruled out.",
        payload={"status": "Out"}, authoritative=authoritative,
        model_extracted=model_extracted,
    )


def _claim(details: dict[str, object] | None = None) -> ExtractedEventClaim:
    return ExtractedEventClaim(
        event_type=EventType.INJURY_STATUS, player_id="evans", player_name="Mike Evans",
        team="TB", effective_at=datetime(2026, 9, 10, tzinfo=timezone.utc),
        summary="Mike Evans ruled out", details=details or {"status": "Out"},
    )


def _seed_two_leagues(db) -> None:
    db.executemany(
        """
        INSERT INTO leagues (league_id, name, season, scoring_settings, roster_positions, settings_blob)
        VALUES (?, ?, '2026', '{}', '[]', '{}')
        """,
        [("affected", "Affected League"), ("unaffected", "Unaffected League")],
    )
    db.executemany(
        """
        INSERT INTO players (player_id, full_name, position, team, metadata_blob)
        VALUES (?, ?, ?, ?, '{}')
        """,
        [
            ("evans", "Mike Evans", "WR", "TB"),
            ("backup", "Bucs Backup", "WR", "TB"),
            ("user_wr", "User Wideout", "WR", "NYG"),
            ("other", "Other Player", "RB", "BAL"),
        ],
    )
    db.executemany(
        """
        INSERT INTO rosters (
            id, league_id, roster_id, owner_id, owner_display_name,
            starters, players, reserve, taxi
        ) VALUES (?, ?, ?, ?, ?, ?, ?, '[]', '[]')
        """,
        [
            (1, "affected", 1, "me", "Me", '["user_wr"]', '["user_wr","other"]'),
            (2, "affected", 2, "rival-a", "Rival A", '["evans"]', '["evans"]'),
            (3, "unaffected", 1, "me", "Me", '["other"]', '["other"]'),
            (4, "unaffected", 2, "rival-b", "Rival B", '["backup"]', '["backup"]'),
        ],
    )
    db.executemany(
        """
        INSERT INTO player_adp_baseline (player_id, player_name, position, adp, adp_source)
        VALUES (?, ?, 'WR', ?, 'test')
        """,
        [("evans", "Mike Evans", 35.0), ("backup", "Bucs Backup", 160.0),
         ("user_wr", "User Wideout", 95.0)],
    )
    db.execute(
        """
        INSERT INTO pick_values (
            id, league_id, pick_owner_roster_id, pick_year, pick_round,
            expected_draft_slot, base_value, timed_value, league_adjusted_value,
            demand_adjusted_value, timing_label, timing_reasoning
        ) VALUES (1, 'affected', 2, 2027, 1, 7.0, .5, .5, .5, .5, 'hold', 'test')
        """
    )


def test_failed_refresh_preserves_last_good_snapshot_and_marks_degraded(db) -> None:
    service = FreshnessService(ContextRepo(db))
    first = service.mark_source_result(
        league_id="league", domain="market", source_id="fantasycalc",
        parsed_successfully=True, record_count=12,
    )
    failed = service.mark_source_result(
        league_id="league", domain="market", source_id="fantasycalc",
        parsed_successfully=False, record_count=0, notes="timeout",
    )

    assert failed.status == "degraded"
    assert failed.is_stale is True
    assert failed.last_updated == first.last_updated
    assert failed.fetched_at is not None
    assert "last confirmed snapshot" in (failed.warning or "")


def test_zero_market_rows_cannot_be_green(db) -> None:
    tag = FreshnessService(ContextRepo(db)).mark_source_result(
        league_id="league", domain="market", source_id="fantasycalc",
        parsed_successfully=True, record_count=0, authoritative_empty=False,
    )
    assert tag.status == "degraded"
    assert tag.is_stale is True
    assert tag.last_updated is None

    batch = LocalLeagueSource(db, "run").collect({"fantasycalc:market_values"})[0]
    assert batch.outcome is not None
    assert batch.outcome.status == "partial"


def test_authoritative_or_two_public_sources_confirm_but_single_model_does_not(db) -> None:
    store = IntelligenceStore(db)
    run = store.start_run("test")
    model_observation = store.save_observation(
        _observation(run, "news-one", model_extracted=True)
    )
    event = store.upsert_claim(model_observation, _claim())
    assert event.verification_state is VerificationState.WATCH

    second = store.save_observation(_observation(run, "news-two"))
    event = store.upsert_claim(second, _claim())
    assert event.verification_state is VerificationState.CONFIRMED

    official_claim = _claim({"status": "Questionable"})
    official = store.save_observation(_observation(run, "nfl-injuries", authoritative=True))
    official_event = store.upsert_claim(official, official_claim)
    assert official_event.verification_state in {
        VerificationState.CONFIRMED,
        VerificationState.CONFLICTED,
    }


def test_conflicting_claims_are_explicit_and_not_actionable(db) -> None:
    _seed_two_leagues(db)
    store = IntelligenceStore(db)
    run = store.start_run("test")
    first = store.save_observation(_observation(run, "official-a", authoritative=True))
    event = store.upsert_claim(first, _claim({"status": "Out"}))
    second = store.save_observation(_observation(run, "official-b", authoritative=True))
    store.upsert_claim(second, _claim({"status": "Active"}))
    event = store.get_event(event.event_id)

    assert event.verification_state is VerificationState.CONFLICTED
    impacts = LeagueImpactEngine(db).compute(event)
    assert impacts
    assert all(not impact.actionable for impact in impacts)
    assert all(all(value == 0 for value in impact.impact_summary.deltas.values()) for impact in impacts)
    assert db.execute(
        "SELECT COUNT(*) FROM canonical_player_projections WHERE event_id = ?",
        [event.event_id],
    ).fetchone()[0] == 0


def test_seeded_injury_rebuilds_cross_league_consequences_without_irrelevant_action(db) -> None:
    _seed_two_leagues(db)
    store = IntelligenceStore(db)
    run = store.start_run("test")
    observation = store.save_observation(_observation(run, "nfl-injuries", authoritative=True))
    event = store.upsert_claim(observation, _claim())

    impacts = LeagueImpactEngine(db).compute(event)
    store.replace_impacts(event.event_id, impacts)
    types = {impact.impact_type for impact in impacts}
    direct = next(impact for impact in impacts if impact.impact_type == "direct_owner")

    assert direct.impact_summary.deltas["player_value"] < 0
    assert direct.impact_summary.deltas["pick_trajectory"] < 0
    assert direct.impact_summary.after["positional_need"] in {"high", "medium", "low"}
    assert "waiver_opportunity" in types
    assert "trade_posture" in types
    assert any("backup" in impact.impact_summary.affected_asset_ids for impact in impacts)
    assert not any(
        impact.actionable and impact.league_id == "unaffected" for impact in impacts
    )
    projection_rows = db.execute(
        """
        SELECT player_id, value_before, value_after
        FROM canonical_player_projections WHERE event_id = ? ORDER BY player_id
        """,
        [event.event_id],
    ).fetchall()
    assert projection_rows
    assert any(row[0] == "evans" and row[2] < row[1] for row in projection_rows)

    brief_items = MorningBriefBuilder(store).build()
    best_moves = [item for item in brief_items if item.lane == "best_move"]
    assert len(best_moves) <= 5
    assert all(sum(item.league_id == league for item in best_moves) <= 3 for league in {"affected", "unaffected"})
    assert not any(item.league_id == "unaffected" for item in best_moves)

    outcome = SourceOutcome(
        source_id="nfl-injuries", status="complete", records_seen=1,
        observations_written=1, events_written=1,
    )
    first_brief = store.publish_brief(
        run_id=run, status="ready", items=brief_items, outcomes=[outcome]
    )
    second_brief = store.publish_brief(
        run_id="equivalent-rerun", status="ready",
        items=MorningBriefBuilder(store).build(), outcomes=[outcome],
    )
    assert second_brief.brief_id == first_brief.brief_id
    assert db.execute("SELECT COUNT(*) FROM daily_briefs").fetchone()[0] == 1


async def test_fixed_morning_bundle_preserves_actions_during_partial_outage(
    db, monkeypatch
) -> None:
    _seed_two_leagues(db)
    holder: dict[str, str] = {}

    def healthy_collect(
        source: object, source_ids: set[str] | None = None
    ) -> list[SourceBatch]:
        del source_ids
        run_id = source._run_id  # type: ignore[attr-defined]
        holder["run_id"] = run_id
        observation = _observation(run_id, "nflreadpy:injuries", authoritative=True)
        return [SourceBatch(
            source_id="nflreadpy:injuries", domain="injuries",
            observations=[observation], claims=[(observation, _claim())],
            outcome=SourceOutcome(source_id="nflreadpy:injuries", status="complete",
                records_seen=1, observations_written=1, events_written=1),
            coverage_through=datetime.now(timezone.utc),
        )]

    monkeypatch.setattr("fantasy.intelligence.runner.NflreadpySource.collect", healthy_collect)
    monkeypatch.setattr(
        "fantasy.intelligence.runner.LocalLeagueSource.collect",
        lambda self, source_ids=None: [],
    )

    first = await FreshIntelligenceRunner(db).run(scheduled=True)
    first_brief = IntelligenceStore(db).get_brief(datetime.now().date())
    first_actions = [item.headline for item in first_brief.items if item.lane == "best_move"]

    assert first.status == "complete"
    assert first_actions

    def failed_collect(
        source: object, source_ids: set[str] | None = None
    ) -> list[SourceBatch]:
        del source_ids
        now = datetime.now(timezone.utc)
        observation = SourceObservation(
            observation_id=str(uuid4()), run_id=source._run_id,  # type: ignore[attr-defined]
            source_id="nflreadpy:injuries", source_tier=SourceTier.STRUCTURED,
            fetched_at=now, content_hash=hashlib.sha256(str(uuid4()).encode()).hexdigest(),
            parse_status=ParseStatus.UNAVAILABLE, evidence_excerpt="timeout",
            payload={"error": "timeout"}, authoritative=True,
        )
        return [SourceBatch(
            source_id="nflreadpy:injuries", domain="injuries", observations=[observation],
            outcome=SourceOutcome(source_id="nflreadpy:injuries", status="failed", message="timeout"),
        )]

    monkeypatch.setattr("fantasy.intelligence.runner.NflreadpySource.collect", failed_collect)
    second = await FreshIntelligenceRunner(db).run(scheduled=True)
    second_brief = IntelligenceStore(db).get_brief(datetime.now().date())
    second_actions = [item.headline for item in second_brief.items if item.lane == "best_move"]

    assert second.status == "degraded"
    assert second_brief.status == "degraded"
    assert second_brief.brief_id != first_brief.brief_id
    assert second_actions == first_actions
    first_snapshot = IntelligenceStore(db)._get_brief_by_id(first_brief.brief_id)
    assert first_snapshot.status == "ready"
    assert [item.headline for item in first_snapshot.items if item.lane == "best_move"] == first_actions


async def test_unchanged_manual_page_reuses_cached_extraction(
    db, monkeypatch, tmp_path
) -> None:
    document = PublicDocument(
        url="https://example.com/update",
        text="Team update: Mike Evans was ruled out after practice.",
        content_hash="same-content",
        fetched_at=datetime.now(timezone.utc),
        retrieval="http",
        raw_cache_path=tmp_path / "same-content.json",
    )
    calls = 0

    class Extractor:
        async def extract(self, text: str, *, source_url: str):
            nonlocal calls
            del text, source_url
            calls += 1
            return [_claim()]

    async def fetch(self, url: str):
        del self, url
        return document

    monkeypatch.setattr("fantasy.intelligence.runner.PublicPageFetcher.fetch", fetch)
    monkeypatch.setattr(
        "fantasy.intelligence.runner.get_narrative_extractor", lambda: Extractor()
    )

    first = await FreshIntelligenceRunner(db).analyze_url(document.url)
    second = await FreshIntelligenceRunner(db).analyze_url(document.url)

    assert calls == 1
    assert [item.event_id for item in second.events] == [
        item.event_id for item in first.events
    ]


async def test_scoped_refresh_filters_before_source_collection(db, monkeypatch) -> None:
    seen: list[set[str] | None] = []

    def collect(self, source_ids=None):
        del self
        seen.append(source_ids)
        return []

    monkeypatch.setattr("fantasy.intelligence.runner.NflreadpySource.collect", collect)
    monkeypatch.setattr("fantasy.intelligence.runner.LocalLeagueSource.collect", collect)

    await FreshIntelligenceRunner(db).run(source_ids=["nflreadpy:injuries"])

    assert seen == [{"nflreadpy:injuries"}, {"nflreadpy:injuries"}]
