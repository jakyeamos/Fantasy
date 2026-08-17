"""Machine-readable runtime truth for fantasy-agent decision capabilities."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

from fantasy.config import get_settings
from fantasy.data_health import assess_stats_health
from fantasy.decision.calibration import calibration_evidence
from fantasy.decision.feedback_repo import DecisionFeedbackRepo


def _count(conn: duckdb.DuckDBPyConnection, table: str) -> int | None:
    try:
        return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    except duckdb.Error:
        return None


def _scalar(conn: duckdb.DuckDBPyConnection, query: str) -> Any | None:
    try:
        row = conn.execute(query).fetchone()
        return row[0] if row else None
    except duckdb.Error:
        return None


def _market_refresh_evidence(
    conn: duckdb.DuckDBPyConnection,
    *,
    successful_only: bool,
) -> dict[str, Any] | None:
    predicate = "WHERE status = 'success'" if successful_only else ""
    try:
        row = conn.execute(
            f"""
            SELECT id, CAST(run_at AS VARCHAR), source, num_qbs, num_teams, ppr,
                   status, source_rows, matched_rows, matched_unique_rows,
                   unmatched_rows, market_value_rows, coverage_ratio, error_detail
            FROM market_refresh_runs
            {predicate}
            ORDER BY run_at DESC, id DESC
            LIMIT 1
            """
        ).fetchone()
    except duckdb.Error:
        return None
    if row is None:
        return None
    return {
        "id": int(row[0]),
        "run_at": str(row[1]),
        "source": str(row[2]),
        "profile": {
            "num_qbs": int(row[3]),
            "num_teams": int(row[4]),
            "ppr": float(row[5]),
        },
        "status": str(row[6]),
        "source_rows": int(row[7]) if row[7] is not None else None,
        "matched_rows": int(row[8]) if row[8] is not None else None,
        "matched_unique_rows": int(row[9]) if row[9] is not None else None,
        "unmatched_rows": int(row[10]) if row[10] is not None else None,
        "market_value_rows": int(row[11]) if row[11] is not None else None,
        "coverage_ratio": float(row[12]) if row[12] is not None else None,
        "error_detail": str(row[13]) if row[13] is not None else None,
    }


def build_capability_manifest(conn: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    leagues = conn.execute(
        "SELECT league_id, season FROM leagues ORDER BY league_id"
    ).fetchall()
    health = {
        str(league_id): assess_stats_health(conn, int(season)).model_dump()
        for league_id, season in leagues
    }
    health_states = {item["status"] for item in health.values()}
    stats_state = (
        "unavailable"
        if not health
        else "blocked"
        if "blocked" in health_states
        else "degraded"
        if "degraded" in health_states or "missing" in health_states
        else "available"
    )
    market_count = _count(conn, "market_values")
    lineup_count = _count(conn, "lineup_scores")
    player_value_count = _count(conn, "player_values")
    feedback_count = _count(conn, "decision_feedback")
    market_latest = _scalar(
        conn,
        "SELECT CAST(MAX(fetched_at) AS VARCHAR) FROM market_values",
    )
    latest_market_refresh = _market_refresh_evidence(conn, successful_only=True)
    latest_market_attempt = _market_refresh_evidence(conn, successful_only=False)
    presentation_count = _scalar(
        conn,
        "SELECT COUNT(*) FROM decision_feedback WHERE event_type = 'presented'",
    )
    action_count = _scalar(
        conn,
        """
        SELECT COUNT(*) FROM decision_feedback
        WHERE event_type IN ('accepted', 'rejected', 'held', 'completed')
        """,
    )
    labeled_outcome_count = _scalar(
        conn,
        """
        SELECT COUNT(*) FROM decision_feedback
        WHERE event_type = 'outcome' AND outcome_score IS NOT NULL
        """,
    )
    feedback_latest = _scalar(
        conn,
        "SELECT CAST(MAX(created_at) AS VARCHAR) FROM decision_feedback",
    )
    try:
        unresolved = DecisionFeedbackRepo(conn).list_unresolved()
    except duckdb.Error:
        unresolved = None
    calibration = calibration_evidence(conn)
    semantic_scorecards = 0
    try:
        semantic_scorecards = int(
            conn.execute(
                """
                SELECT COUNT(*) FROM team_scorecards
                WHERE computation_json LIKE '%team-scorecard-semantics/1.0%'
                """
            ).fetchone()[0]
        )
    except duckdb.Error:
        pass

    def persisted_state(count: int | None) -> str:
        return (
            "unsupported" if count is None else "available" if count > 0 else "degraded"
        )

    return {
        "schema_version": "fantasy-agent-capabilities/1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "capabilities": {
            "read_only_agent_context": {
                "provider": "native",
                "runtime_state": "available",
                "interface": "python -m fantasy.agent_context --question <text> --json",
                "schema_version": "agent-context/2.0",
            },
            "stats_integrity_gate": {
                "provider": "native",
                "runtime_state": stats_state,
                "league_health": health,
            },
            "score_semantics": {
                "provider": "native",
                "runtime_state": "available" if semantic_scorecards else "degraded",
                "semantic_scorecard_rows": semantic_scorecards,
                "model_version": "team-scorecard/2.0",
            },
            "decision_packet": {
                "provider": "native",
                "runtime_state": "available",
                "schema_version": "decision-packet/1.0",
            },
            "recorded_advice": {
                "provider": "native",
                "runtime_state": "available",
                "interface": "fantasy-advise --question <text> --json",
                "presentation_semantics": "record_by_default",
            },
            "lineup_evidence": {
                "provider": "native",
                "runtime_state": persisted_state(lineup_count),
                "persisted_rows": lineup_count,
            },
            "player_value_evidence": {
                "provider": "native",
                "runtime_state": persisted_state(player_value_count),
                "persisted_rows": player_value_count,
            },
            "external_market_values": {
                "provider": "native",
                "runtime_state": persisted_state(market_count),
                "persisted_rows": market_count,
                "latest_fetched_at": str(market_latest) if market_latest else None,
                "latest_refresh": latest_market_refresh,
                "latest_attempt": latest_market_attempt,
            },
            "decision_feedback": {
                "provider": "native" if feedback_count is not None else "unsupported",
                "runtime_state": "available"
                if feedback_count is not None
                else "unsupported",
                "persisted_rows": feedback_count,
                "storage_semantics": "append_only",
                "presented_events": int(presentation_count or 0),
                "action_events": int(action_count or 0),
                "labeled_outcomes": int(labeled_outcome_count or 0),
                "latest_event_at": str(feedback_latest) if feedback_latest else None,
            },
            "decision_followups": {
                "provider": "native" if unresolved is not None else "unsupported",
                "runtime_state": "available"
                if unresolved is not None
                else "unsupported",
                "schema_version": "decision-followups/1.0",
                "unresolved_decisions": len(unresolved)
                if unresolved is not None
                else None,
                "due_followups": (
                    sum(1 for decision in unresolved if decision["is_due"])
                    if unresolved is not None
                    else None
                ),
                "next_follow_up_at": (
                    next(
                        (
                            decision["follow_up_at"]
                            for decision in unresolved
                            if decision["follow_up_at"] is not None
                        ),
                        None,
                    )
                    if unresolved is not None
                    else None
                ),
                "interface": "fantasy-feedback --list-open --due-only",
            },
            "decision_calibration": {
                "provider": "native",
                "runtime_state": calibration["status"],
                "evidence": calibration,
            },
            "golden_agent_evaluations": {
                "provider": "native",
                "runtime_state": "verification_required",
                "verification_command": "backend/.venv/bin/pytest -q backend/tests/golden/test_fantasy_agent.py",
            },
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit fantasy-agent capability truth.")
    parser.add_argument("--json", action="store_true")
    parser.parse_args(argv)
    db_path = Path(get_settings().db_path)
    if not db_path.exists():
        print(json.dumps({"error": "database_missing", "database_path": str(db_path)}))
        return 1
    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        manifest = build_capability_manifest(conn)
    finally:
        conn.close()
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
