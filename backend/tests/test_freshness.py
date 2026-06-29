from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fantasy.context.context_repo import ContextRepo
from fantasy.context.freshness_service import FreshnessService


def test_get_tags_marks_stale_data(db) -> None:
    repo = ContextRepo(db)
    updated_at = datetime.now(tz=timezone.utc) - timedelta(days=3)
    repo.upsert_freshness("league_x", "injuries", updated_at, notes=None)

    tags = FreshnessService(
        repo=repo,
        now=lambda: datetime.now(tz=timezone.utc),
    ).get_tags("league_x", ["injuries"])

    assert tags[0].is_stale is True
    assert tags[0].warning is not None


def test_get_tags_marks_fresh_data(db) -> None:
    repo = ContextRepo(db)
    updated_at = datetime.now(tz=timezone.utc) - timedelta(hours=1)
    repo.upsert_freshness("league_x", "injuries", updated_at, notes=None)

    tags = FreshnessService(
        repo=repo,
        now=lambda: datetime.now(tz=timezone.utc),
    ).get_tags("league_x", ["injuries"])

    assert tags[0].is_stale is False
    assert tags[0].warning is None


def test_get_tags_marks_missing_domain_as_stale(db) -> None:
    tags = FreshnessService(
        repo=ContextRepo(db),
        now=lambda: datetime.now(tz=timezone.utc),
    ).get_tags("league_x", ["injuries"])

    assert tags[0].is_stale is True
    assert tags[0].warning is not None


def test_get_tags_uses_global_nonweekly_evidence_refresh(db) -> None:
    repo = ContextRepo(db)
    updated_at = datetime.now(tz=timezone.utc) - timedelta(hours=1)
    repo.upsert_freshness("__global__", "player_metadata", updated_at, notes=None)

    tags = FreshnessService(
        repo=repo,
        now=lambda: datetime.now(tz=timezone.utc),
    ).get_tags("league_x", ["player_metadata"])

    assert tags[0].is_stale is False
    assert tags[0].last_updated is not None
