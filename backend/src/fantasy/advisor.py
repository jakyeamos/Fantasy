"""Grounded fantasy advice with record-by-default decision lifecycle evidence."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import duckdb

from fantasy.agent_context import build_agent_context
from fantasy.config import get_settings
from fantasy.decision.feedback_repo import DecisionFeedbackRepo


def record_presented_packets(
    conn: duckdb.DuckDBPyConnection,
    packets: list[dict[str, Any]],
    *,
    follow_up_at: datetime | None = None,
) -> dict[str, Any]:
    """Append one presentation event for every packet emitted by the advice interface."""

    if follow_up_at is None:
        follow_up_at = datetime.now(timezone.utc) + timedelta(days=30)
    repo = DecisionFeedbackRepo(conn)
    event_ids = [
        repo.record_presentation(packet, follow_up_at=follow_up_at) for packet in packets
    ]
    return {
        "status": "recorded",
        "event_type": "presented",
        "recorded_packets": len(event_ids),
        "event_ids": event_ids,
        "follow_up_at": str(follow_up_at) if follow_up_at else None,
    }


def create_recorded_advice(
    db_path: Path,
    *,
    question: str,
    owner_id: str | None = None,
    owner_display_name: str | None = None,
    league_id: str | None = None,
    stale_after_hours: float = 72.0,
    follow_up_days: int = 30,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build context read-only, then append presentations through a separate connection."""

    if follow_up_days < 1:
        raise ValueError("follow_up_days must be at least one.")
    current = now or datetime.now(timezone.utc)
    follow_up_at = current + timedelta(days=follow_up_days)

    read_conn = duckdb.connect(str(db_path), read_only=True)
    try:
        payload = build_agent_context(
            read_conn,
            question=question,
            owner_id=owner_id,
            owner_display_name=owner_display_name,
            league_id=league_id,
            stale_after_hours=stale_after_hours,
            now=now,
        )
    finally:
        read_conn.close()

    write_conn = duckdb.connect(str(db_path))
    try:
        payload["decision_recording"] = record_presented_packets(
            write_conn,
            payload["decision_packets"],
            follow_up_at=follow_up_at,
        )
    finally:
        write_conn.close()
    payload["database"] = {
        "path": str(db_path),
        "mode": "read_only_context+append_only_feedback",
    }
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Emit grounded fantasy advice and record presented decisions."
    )
    parser.add_argument("--question", required=True)
    parser.add_argument("--owner-id")
    parser.add_argument("--owner-name")
    parser.add_argument("--league-id")
    parser.add_argument("--stale-after-hours", type=float, default=72.0)
    parser.add_argument("--follow-up-days", type=int, default=30)
    parser.add_argument("--json", action="store_true", help="Emit JSON (default output)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    db_path = Path(get_settings().db_path)
    if not db_path.exists():
        print(json.dumps({"error": "database_missing", "database_path": str(db_path)}))
        return 1
    try:
        payload = create_recorded_advice(
            db_path,
            question=args.question,
            owner_id=args.owner_id,
            owner_display_name=args.owner_name,
            league_id=args.league_id,
            stale_after_hours=args.stale_after_hours,
            follow_up_days=args.follow_up_days,
        )
    except (duckdb.Error, ValueError) as exc:
        print(json.dumps({"error": "advice_query_failed", "detail": str(exc)}, indent=2))
        return 1
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
