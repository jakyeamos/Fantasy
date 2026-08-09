from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from fantasy.config import get_settings
from fantasy.decision.feedback_repo import DecisionFeedbackRepo


def _datetime(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Record append-only decision lifecycle events.")
    parser.add_argument("packet", nargs="?", type=Path, help="Legacy DecisionPacket JSON path")
    parser.add_argument("--decision-id", help="Previously presented decision identifier")
    parser.add_argument("--list-open", action="store_true", help="List unresolved decisions")
    parser.add_argument("--due-only", action="store_true", help="Only list due follow-ups")
    parser.add_argument("--as-of", type=_datetime, help="Queue evaluation time (ISO-8601)")
    parser.add_argument(
        "--event",
        choices=["presented", "accepted", "rejected", "held", "completed", "outcome"],
    )
    parser.add_argument("--action-taken")
    parser.add_argument("--outcome")
    parser.add_argument("--outcome-score", type=float)
    parser.add_argument("--follow-up-at", type=_datetime)
    parser.add_argument("--notes")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.list_open:
        if args.packet is not None or args.decision_id is not None or args.event is not None:
            parser.error("--list-open cannot be combined with a packet, --decision-id, or --event")
    elif args.packet is None and args.decision_id is None:
        parser.error("provide a packet path, --decision-id, or --list-open")
    if args.packet is not None and args.decision_id is not None:
        parser.error("provide either a packet path or --decision-id, not both")
    if args.event == "presented" and args.packet is None:
        parser.error("presented events require a packet path")
    if args.due_only and not args.list_open:
        parser.error("--due-only requires --list-open")

    conn = duckdb.connect(str(get_settings().db_path), read_only=args.list_open)
    try:
        repo = DecisionFeedbackRepo(conn)
        if args.list_open:
            decisions = repo.list_unresolved(as_of=args.as_of, due_only=args.due_only)
            print(
                json.dumps(
                    {
                        "schema_version": "decision-followups/1.0",
                        "status": "available",
                        "due_only": args.due_only,
                        "count": len(decisions),
                        "decisions": decisions,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        if args.packet is not None:
            packet = json.loads(args.packet.read_text())
            if args.event == "presented":
                row_id = repo.record_presentation(
                    packet,
                    follow_up_at=args.follow_up_at,
                )
                event_type = "presented"
            else:
                row_id = repo.record_feedback(
                    packet,
                    action_taken=args.action_taken,
                    outcome=args.outcome,
                    notes=args.notes,
                )
                event_type = "outcome" if args.outcome is not None else "feedback"
        else:
            event_type = args.event or "held"
            row_id = repo.record_event(
                args.decision_id,
                event_type=event_type,
                outcome=args.outcome,
                outcome_score=args.outcome_score,
                follow_up_at=args.follow_up_at,
                notes=args.notes,
            )
    finally:
        conn.close()
    print(
        json.dumps(
            {"status": "recorded", "feedback_id": row_id, "event_type": event_type}
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
