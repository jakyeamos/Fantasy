from datetime import datetime
from types import SimpleNamespace

import duckdb
import pytest

from fantasy.decision.calibration import (
    calibration_evidence,
    run_decision_calibration,
    trade_calibration_evidence,
)
from fantasy.decision.feedback_cli import main as feedback_main
from fantasy.decision.feedback_repo import DecisionFeedbackRepo
from test_support.schema_sql import SCHEMA_SQL


def _packet() -> dict:
    return {
        "schema_version": "decision-packet/1.0",
        "decision_id": "decision-1",
        "league": {"league_id": "league_x", "roster_id": 1},
        "recommendation": {"action": "request_details", "confidence": 0.6},
    }


def _trade_packet(decision_id: str, confidence: float) -> dict:
    packet = _packet()
    packet["decision_id"] = decision_id
    packet["decision_type"] = "trade"
    packet["league"]["league_id"] = "league_x"
    packet["recommendation"]["confidence"] = confidence
    return packet


def test_feedback_is_append_only_and_retrievable(db):
    repo = DecisionFeedbackRepo(db)
    repo.record_feedback(_packet(), action_taken="held", notes="Awaiting years")
    repo.record_feedback(_packet(), action_taken="declined", outcome="no_trade")

    rows = repo.list_feedback("decision-1")

    assert [row["action_taken"] for row in rows] == ["held", "declined"]
    assert rows[1]["outcome"] == "no_trade"


def test_calibration_requires_labeled_sample_and_surfaces_metrics(db):
    repo = DecisionFeedbackRepo(db)
    with pytest.raises(ValueError, match="at least one"):
        repo.record_calibration(
            model_name="decision", model_version="1", season="2026",
            sample_size=0, metrics={}
        )
    repo.record_calibration(
        model_name="decision",
        model_version="1",
        season="2026",
        sample_size=12,
        metrics={"brier_score": 0.18},
    )

    evidence = calibration_evidence(db)

    assert evidence["status"] == "available"
    assert evidence["sample_size"] == 12
    assert evidence["metrics"]["brier_score"] == 0.18


def test_trade_calibration_unlocks_at_scoped_labeled_evidence_floor(db):
    repo = DecisionFeedbackRepo(db)
    for decision_id, confidence, outcome_score in [
        ("trade-1", 0.8, 1.0),
        ("trade-2", 0.4, 0.0),
    ]:
        packet = _trade_packet(decision_id, confidence)
        repo.record_presentation(packet)
        repo.record_event(
            decision_id,
            event_type="outcome",
            outcome=(
                "recommendation_correct"
                if outcome_score == 1.0
                else "recommendation_incorrect"
            ),
            outcome_score=outcome_score,
        )

    unrelated = _packet()
    unrelated["decision_id"] = "roster-1"
    repo.record_presentation(unrelated)
    repo.record_event(
        "roster-1",
        event_type="outcome",
        outcome="recommendation_correct",
        outcome_score=1.0,
    )
    repo.record_calibration(
        model_name="decision",
        model_version="1",
        season="2026",
        sample_size=10,
        metrics={"brier_score": 0.01},
    )

    unavailable = trade_calibration_evidence(
        db, league_id="league_x", minimum_sample_size=3
    )
    assert unavailable["status"] == "unavailable"
    assert unavailable["sample_size"] == 2
    assert unavailable["captured_decisions"] == 2
    assert unavailable["progress_percent"] == pytest.approx(66.7)
    assert unavailable["metrics"] is None

    available = trade_calibration_evidence(
        db, league_id="league_x", minimum_sample_size=2
    )
    assert available["status"] == "available"
    assert available["win_probability_status"] == "available"
    assert available["sample_size"] == 2
    assert available["metrics"]["brier_score"] == pytest.approx(0.1)

    other_league = trade_calibration_evidence(
        db, league_id="other_league", minimum_sample_size=1
    )
    assert other_league["status"] == "unavailable"
    assert other_league["sample_size"] == 0


def test_decision_lifecycle_records_presentation_and_resolves_events_by_id(db):
    repo = DecisionFeedbackRepo(db)

    presentation_id = repo.record_presentation(_packet())
    accepted_id = repo.record_event(
        "decision-1",
        event_type="accepted",
        notes="Manager accepted the recommendation",
    )
    outcome_id = repo.record_event(
        "decision-1",
        event_type="outcome",
        outcome="recommendation_correct",
        outcome_score=1.0,
    )

    assert presentation_id < accepted_id < outcome_id
    rows = repo.list_feedback("decision-1")
    assert [row["event_type"] for row in rows] == ["presented", "accepted", "outcome"]
    assert rows[-1]["outcome_score"] == 1.0


def test_repeated_presentation_is_idempotent_without_collapsing_lifecycle_events(db):
    repo = DecisionFeedbackRepo(db)
    first_follow_up = datetime(2026, 9, 1, 12, 0, 0)
    repeated_packet = _packet()
    repeated_packet["recommendation"]["confidence"] = 0.7

    presentation_id = repo.record_presentation(
        _packet(), follow_up_at=first_follow_up
    )
    repeated_id = repo.record_presentation(
        repeated_packet, follow_up_at=datetime(2026, 10, 1, 12, 0, 0)
    )

    accepted_id = repo.record_event("decision-1", event_type="accepted")
    outcome_id = repo.record_event(
        "decision-1",
        event_type="outcome",
        outcome="recommendation_correct",
        outcome_score=1.0,
    )

    assert repeated_id == presentation_id
    assert accepted_id > presentation_id
    assert outcome_id > accepted_id
    assert db.execute(
        "SELECT COUNT(*) FROM decision_feedback WHERE decision_id = 'decision-1'"
    ).fetchone()[0] == 3
    rows = repo.list_feedback("decision-1")
    assert [row["event_type"] for row in rows] == [
        "presented",
        "accepted",
        "outcome",
    ]
    assert rows[0]["follow_up_at"] == "2026-09-01 12:00:00"


def test_unresolved_queue_tracks_due_dates_and_resolution_without_duplicates(db):
    repo = DecisionFeedbackRepo(db)
    follow_up_at = datetime(2026, 9, 1, 12, 0, 0)
    repo.record_presentation(_packet(), follow_up_at=follow_up_at)

    assert repo.list_unresolved(as_of=datetime(2026, 8, 31, 12, 0, 0)) == [
        {
            "decision_id": "decision-1",
            "league_id": "league_x",
            "roster_id": 1,
            "question": None,
            "recommendation_action": "request_details",
            "confidence": 0.6,
            "latest_event": "presented",
            "resolution_state": "awaiting_action",
            "follow_up_at": "2026-09-01 12:00:00",
            "is_due": False,
        }
    ]
    assert repo.list_unresolved(
        as_of=datetime(2026, 9, 2, 12, 0, 0), due_only=True
    )[0]["is_due"] is True

    repo.record_event(
        "decision-1",
        event_type="accepted",
        follow_up_at=datetime(2026, 10, 1, 12, 0, 0),
    )
    pending = repo.list_unresolved(as_of=datetime(2026, 9, 2, 12, 0, 0))
    assert len(pending) == 1
    assert pending[0]["resolution_state"] == "awaiting_outcome"
    assert pending[0]["follow_up_at"] == "2026-10-01 12:00:00"

    repo.record_event(
        "decision-1",
        event_type="outcome",
        outcome="recommendation_correct",
        outcome_score=1.0,
    )
    assert repo.list_unresolved(as_of=datetime(2026, 10, 2, 12, 0, 0)) == []
    assert calibration_evidence(db)["sample_size"] == 1


def test_held_event_preserves_or_reschedules_follow_up(db):
    repo = DecisionFeedbackRepo(db)
    repo.record_presentation(
        _packet(), follow_up_at=datetime(2026, 9, 1, 12, 0, 0)
    )

    repo.record_event("decision-1", event_type="held")
    assert repo.list_unresolved()[0]["follow_up_at"] == "2026-09-01 12:00:00"

    repo.record_event(
        "decision-1",
        event_type="held",
        follow_up_at=datetime(2026, 9, 15, 12, 0, 0),
    )
    assert repo.list_unresolved()[0]["follow_up_at"] == "2026-09-15 12:00:00"


def test_feedback_cli_lists_due_unresolved_decisions(tmp_path, monkeypatch, capsys):
    db_path = tmp_path / "followups.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        for statement in SCHEMA_SQL:
            conn.execute(statement)
        DecisionFeedbackRepo(conn).record_presentation(
            _packet(), follow_up_at=datetime(2026, 9, 1, 12, 0, 0)
        )
    finally:
        conn.close()
    monkeypatch.setattr(
        "fantasy.decision.feedback_cli.get_settings",
        lambda: SimpleNamespace(db_path=str(db_path)),
    )

    assert feedback_main(
        ["--list-open", "--due-only", "--as-of", "2026-09-02T12:00:00Z"]
    ) == 0

    output = capsys.readouterr().out
    assert '"schema_version": "decision-followups/1.0"' in output
    assert '"decision_id": "decision-1"' in output
    assert '"is_due": true' in output


def test_decision_lifecycle_rejects_invalid_or_orphaned_outcomes(db):
    repo = DecisionFeedbackRepo(db)

    with pytest.raises(ValueError, match="No presented decision"):
        repo.record_event("missing", event_type="accepted")

    repo.record_presentation(_packet())
    with pytest.raises(ValueError, match="outcome_score"):
        repo.record_event("decision-1", event_type="outcome", outcome="unknown")
    with pytest.raises(ValueError, match="between 0 and 1"):
        repo.record_event(
            "decision-1",
            event_type="outcome",
            outcome="recommendation_correct",
            outcome_score=1.5,
        )


def test_calibration_runner_fails_closed_below_minimum_sample(db):
    repo = DecisionFeedbackRepo(db)
    repo.record_presentation(_packet())
    repo.record_event(
        "decision-1",
        event_type="outcome",
        outcome="recommendation_correct",
        outcome_score=1.0,
    )

    result = run_decision_calibration(db, season="2026", min_sample_size=2)

    assert result["status"] == "insufficient_sample"
    assert result["sample_size"] == 1
    assert result["minimum_sample_size"] == 2
    assert db.execute("SELECT COUNT(*) FROM decision_calibration_runs").fetchone()[0] == 0


def test_calibration_runner_records_versioned_metrics_from_latest_outcomes(db):
    repo = DecisionFeedbackRepo(db)
    for decision_id, confidence, outcome_score in [
        ("d1", 0.8, 1.0),
        ("d2", 0.7, 0.0),
        ("d3", 0.4, 0.0),
    ]:
        packet = _packet()
        packet["decision_id"] = decision_id
        packet["recommendation"]["confidence"] = confidence
        repo.record_presentation(packet)
        repo.record_event(
            decision_id,
            event_type="outcome",
            outcome=(
                "recommendation_correct"
                if outcome_score == 1.0
                else "recommendation_incorrect"
            ),
            outcome_score=outcome_score,
        )

    result = run_decision_calibration(db, season="2026", min_sample_size=3)

    assert result["status"] == "available"
    assert result["sample_size"] == 3
    assert result["model_name"] == "agent-decision"
    assert result["model_version"] == "decision-packet/1.0+calibration/1.0"
    assert result["metrics"]["brier_score"] == pytest.approx(0.23)
    assert result["metrics"]["accuracy_at_0_5"] == pytest.approx(2 / 3)
    assert result["metrics"]["expected_calibration_error"] >= 0
    assert calibration_evidence(db)["status"] == "available"
