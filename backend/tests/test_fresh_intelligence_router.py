from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from fantasy.intelligence.event_store import IntelligenceStore
from fantasy.intelligence.fresh_models import (
    EventType,
    ExtractedEventClaim,
    ParseStatus,
    SourceObservation,
    SourceOutcome,
    SourceTier,
)
from fantasy.main import create_app
from fantasy.routers.deps import get_read_db_conn, get_write_db_conn


def _override_conn(conn):
    def _getter():
        yield conn

    return _getter


def _client(db) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(db)
    app.dependency_overrides[get_write_db_conn] = _override_conn(db)
    return TestClient(app)


def test_today_reports_explicit_missing_run(db) -> None:
    response = _client(db).get("/v2/briefs/today")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "brief_not_run"


def test_event_evidence_detail_and_review_are_versioned_routes(db) -> None:
    store = IntelligenceStore(db)
    run_id = store.start_run("test")
    now = datetime.now(timezone.utc)
    observation = store.save_observation(SourceObservation(
        observation_id=str(uuid4()),
        run_id=run_id,
        source_id="secondary:test",
        source_tier=SourceTier.PUBLIC,
        url="https://example.com/story",
        fetched_at=now,
        observed_at=now,
        content_hash="router-evidence",
        parse_status=ParseStatus.PARSED,
        evidence_excerpt="Mike Evans was ruled out.",
    ))
    event = store.upsert_claim(observation, ExtractedEventClaim(
        event_type=EventType.INJURY_STATUS,
        player_id="evans",
        player_name="Mike Evans",
        summary="Mike Evans ruled out",
        details={"status": "Out"},
    ))
    client = _client(db)

    detail = client.get(f"/v2/events/{event.event_id}")
    queue = client.get("/v2/intelligence/review")
    reviewed = client.post(
        f"/v2/events/{event.event_id}/review",
        json={"decision": "confirm", "notes": "verified locally"},
    )

    assert detail.status_code == 200
    assert detail.json()["observations"][0]["evidence_excerpt"] == "Mike Evans was ruled out."
    assert [item["event_id"] for item in queue.json()] == [event.event_id]
    assert reviewed.status_code == 200
    assert reviewed.json()["event"]["verification_state"] == "confirmed"
    assert client.get("/v2/intelligence/review").json() == []

    review_row = db.execute(
        "SELECT decision, notes FROM event_reviews WHERE event_id = ?",
        [event.event_id],
    ).fetchone()
    assert review_row == ("confirm", "verified locally")


def test_today_brief_round_trips_source_coverage(db) -> None:
    store = IntelligenceStore(db)
    run_id = store.start_run("test")
    now = datetime.now(timezone.utc)
    store.publish_brief(
        run_id=run_id,
        status="empty",
        items=[],
        outcomes=[SourceOutcome(
            source_id="nflreadpy:injuries",
            status="complete",
            fetched_at=now,
            coverage_through=now,
        )],
    )

    response = _client(db).get("/v2/briefs/today")

    assert response.status_code == 200
    assert response.json()["brief_date"] == date.today().isoformat()
    assert response.json()["source_health"][0]["coverage_through"] is not None
