from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

import duckdb


class DecisionFeedbackRepo:
    """Append-only outcome evidence for future model calibration."""

    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def _next_id(self, table: str) -> int:
        row = self._conn.execute(
            f"SELECT COALESCE(MAX(id), 0) + 1 FROM {table}"
        ).fetchone()
        return int(row[0])

    def _record_snapshot(
        self,
        packet: dict[str, Any],
        *,
        event_type: str,
        action_taken: str | None = None,
        outcome: str | None = None,
        outcome_score: float | None = None,
        follow_up_at: datetime | None = None,
        resolution_state: str | None = None,
        notes: str | None = None,
    ) -> int:
        league = packet["league"]
        recommendation = packet["recommendation"]
        row_id = self._next_id("decision_feedback")
        self._conn.execute(
            """
            INSERT INTO decision_feedback (
                id, decision_id, league_id, roster_id, packet_version,
                recommendation_action, confidence, event_type, action_taken,
                outcome, outcome_score, follow_up_at, resolution_state, notes,
                packet_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                row_id,
                packet["decision_id"],
                league["league_id"],
                int(league["roster_id"]),
                packet["schema_version"],
                recommendation["action"],
                float(recommendation["confidence"]),
                event_type,
                action_taken,
                outcome,
                outcome_score,
                self._normalize_datetime(follow_up_at),
                resolution_state or self._resolution_state(event_type),
                notes,
                json.dumps(packet, separators=(",", ":"), default=str),
            ],
        )
        return row_id

    @staticmethod
    def _normalize_datetime(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    @staticmethod
    def _resolution_state(event_type: str) -> str:
        if event_type == "outcome":
            return "resolved"
        if event_type in {"accepted", "rejected", "completed"}:
            return "awaiting_outcome"
        return "awaiting_action"

    def record_presentation(
        self,
        packet: dict[str, Any],
        *,
        follow_up_at: datetime | None = None,
        now: datetime | None = None,
    ) -> int:
        """Persist one presentation for a logical decision.

        Presentation is the delivery edge of the decision lifecycle. Replaying
        the same packet, or rebuilding it with fresh evidence, must not create
        another presentation row for the same decision. Other lifecycle events
        remain append-only and are deliberately not included in this lookup.
        """

        existing_id = self._conn.execute(
            """
            SELECT id
            FROM decision_feedback
            WHERE decision_id = ? AND event_type = 'presented'
            ORDER BY created_at, id
            LIMIT 1
            """,
            [packet["decision_id"]],
        ).fetchone()
        if existing_id is not None:
            return int(existing_id[0])

        if follow_up_at is None:
            current = now or datetime.now(timezone.utc)
            follow_up_at = current + timedelta(days=30)

        return self._record_snapshot(
            packet,
            event_type="presented",
            action_taken="presented",
            follow_up_at=follow_up_at,
        )

    def _latest_snapshot(self, decision_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            """
            SELECT packet_json, follow_up_at, resolution_state
            FROM decision_feedback
            WHERE decision_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            [decision_id],
        ).fetchone()
        if row is None:
            return None
        return {
            "packet": json.loads(row[0]),
            "follow_up_at": row[1],
            "resolution_state": str(row[2]),
        }

    def latest_packet(self, decision_id: str) -> dict[str, Any] | None:
        """Return the latest packet snapshot for a logical decision."""

        latest = self._latest_snapshot(decision_id)
        return latest["packet"] if latest is not None else None

    def record_event(
        self,
        decision_id: str,
        *,
        event_type: str,
        outcome: str | None = None,
        outcome_score: float | None = None,
        follow_up_at: datetime | None = None,
        notes: str | None = None,
    ) -> int:
        allowed = {"accepted", "rejected", "held", "completed", "outcome"}
        if event_type not in allowed:
            raise ValueError(f"Unsupported decision event type: {event_type}")
        latest = self._latest_snapshot(decision_id)
        if latest is None:
            raise ValueError(f"No presented decision exists for {decision_id}.")
        if event_type == "outcome" and outcome_score is None:
            raise ValueError("outcome events require outcome_score.")
        if event_type != "outcome" and outcome_score is not None:
            raise ValueError("outcome_score is only valid for outcome events.")
        if outcome_score is not None and not 0.0 <= outcome_score <= 1.0:
            raise ValueError("outcome_score must be between 0 and 1.")
        return self._record_snapshot(
            latest["packet"],
            event_type=event_type,
            action_taken=event_type,
            outcome=outcome,
            outcome_score=outcome_score,
            follow_up_at=follow_up_at or latest["follow_up_at"],
            notes=notes,
        )

    def record_feedback(
        self,
        packet: dict[str, Any],
        *,
        action_taken: str | None = None,
        outcome: str | None = None,
        notes: str | None = None,
    ) -> int:
        event_type = "outcome" if outcome is not None else "feedback"
        return self._record_snapshot(
            packet,
            event_type=event_type,
            action_taken=action_taken,
            outcome=outcome,
            notes=notes,
        )

    def list_feedback(self, decision_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT id, CAST(created_at AS VARCHAR), event_type, action_taken,
                   outcome, outcome_score, CAST(follow_up_at AS VARCHAR),
                   resolution_state, notes, recommendation_action, confidence
            FROM decision_feedback
            WHERE decision_id = ?
            ORDER BY created_at, id
            """,
            [decision_id],
        ).fetchall()
        return [
            {
                "id": int(row[0]),
                "created_at": str(row[1]),
                "event_type": str(row[2]),
                "action_taken": str(row[3]) if row[3] is not None else None,
                "outcome": str(row[4]) if row[4] is not None else None,
                "outcome_score": float(row[5]) if row[5] is not None else None,
                "follow_up_at": str(row[6]) if row[6] is not None else None,
                "resolution_state": str(row[7]),
                "notes": str(row[8]) if row[8] is not None else None,
                "recommendation_action": str(row[9]),
                "confidence": float(row[10]),
            }
            for row in rows
        ]

    def list_unresolved(
        self,
        *,
        as_of: datetime | None = None,
        due_only: bool = False,
        league_id: str | None = None,
        decision_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return one latest, unresolved follow-up per logical decision."""

        current = self._normalize_datetime(as_of or datetime.now(timezone.utc))
        filters = ["recency_rank = 1", "resolution_state != 'resolved'"]
        params: list[Any] = []
        if league_id is not None:
            filters.append("league_id = ?")
            params.append(league_id)
        if decision_type is not None:
            filters.append("json_extract_string(packet_json, '$.decision_type') = ?")
            params.append(decision_type)
        rows = self._conn.execute(
            f"""
            SELECT decision_id, league_id, roster_id, recommendation_action,
                   confidence, event_type, resolution_state, follow_up_at,
                   packet_json
            FROM (
                SELECT *, ROW_NUMBER() OVER (
                    PARTITION BY decision_id
                    ORDER BY created_at DESC, id DESC
                ) AS recency_rank
                FROM decision_feedback
            ) latest
            WHERE {' AND '.join(filters)}
            ORDER BY follow_up_at NULLS LAST, decision_id
            """,
            params,
        ).fetchall()
        decisions: list[dict[str, Any]] = []
        for row in rows:
            follow_up_at = self._normalize_datetime(row[7])
            is_due = follow_up_at is not None and follow_up_at <= current
            if due_only and not is_due:
                continue
            packet = json.loads(row[8])
            decisions.append(
                {
                    "decision_id": str(row[0]),
                    "league_id": str(row[1]),
                    "roster_id": int(row[2]),
                    "question": packet.get("question"),
                    "recommendation_action": str(row[3]),
                    "confidence": float(row[4]),
                    "latest_event": str(row[5]),
                    "resolution_state": str(row[6]),
                    "follow_up_at": str(follow_up_at) if follow_up_at else None,
                    "is_due": is_due,
                }
            )
        return decisions

    def record_calibration(
        self,
        *,
        model_name: str,
        model_version: str,
        season: str,
        sample_size: int,
        metrics: dict[str, Any],
        notes: str | None = None,
    ) -> int:
        if sample_size < 1:
            raise ValueError("Calibration requires at least one labeled decision.")
        row_id = self._next_id("decision_calibration_runs")
        self._conn.execute(
            """
            INSERT INTO decision_calibration_runs (
                id, model_name, model_version, season, sample_size, metrics_json, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                row_id,
                model_name,
                model_version,
                season,
                sample_size,
                json.dumps(metrics, separators=(",", ":")),
                notes,
            ],
        )
        return row_id
