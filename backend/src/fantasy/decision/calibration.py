from __future__ import annotations

import json
from typing import Any

import duckdb

from fantasy.decision.feedback_repo import DecisionFeedbackRepo

MODEL_NAME = "agent-decision"
MODEL_VERSION = "decision-packet/1.0+calibration/1.0"
DEFAULT_MINIMUM_SAMPLE_SIZE = 20


def calibration_evidence(conn: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    """Return calibration truth without turning mere model execution into validation."""

    try:
        row = conn.execute(
            """
            SELECT model_name, model_version, season, sample_size, metrics_json,
                   CAST(run_at AS VARCHAR), notes
            FROM decision_calibration_runs
            ORDER BY run_at DESC, id DESC
            LIMIT 1
            """
        ).fetchone()
    except duckdb.Error:
        row = None
    if row:
        return {
            "status": "available",
            "model_name": str(row[0]),
            "model_version": str(row[1]),
            "season": str(row[2]),
            "sample_size": int(row[3]),
            "metrics": json.loads(row[4] or "{}"),
            "run_at": str(row[5]),
            "notes": str(row[6]) if row[6] is not None else None,
        }

    try:
        retrospective_count = int(
            conn.execute("SELECT COUNT(*) FROM retrospective_runs").fetchone()[0]
        )
    except duckdb.Error:
        retrospective_count = 0
    return {
        "status": "unavailable",
        "sample_size": int(
            conn.execute(
                """
                SELECT COUNT(DISTINCT decision_id)
                FROM decision_feedback
                WHERE event_type = 'outcome' AND outcome_score IS NOT NULL
                """
            ).fetchone()[0]
        ),
        "minimum_sample_size": DEFAULT_MINIMUM_SAMPLE_SIZE,
        "retrospective_run_count": retrospective_count,
        "message": "No decision calibration run has been recorded.",
    }


def _expected_calibration_error(rows: list[tuple[float, float]]) -> float:
    buckets: dict[int, list[tuple[float, float]]] = {}
    for confidence, outcome_score in rows:
        bucket = min(int(confidence * 5), 4)
        buckets.setdefault(bucket, []).append((confidence, outcome_score))
    total = len(rows)
    return sum(
        (len(items) / total)
        * abs(
            (sum(confidence for confidence, _ in items) / len(items))
            - (sum(outcome for _, outcome in items) / len(items))
        )
        for items in buckets.values()
    )


def run_decision_calibration(
    conn: duckdb.DuckDBPyConnection,
    *,
    season: str,
    min_sample_size: int = DEFAULT_MINIMUM_SAMPLE_SIZE,
) -> dict[str, Any]:
    """Evaluate latest labeled outcomes and persist metrics only above the evidence floor."""

    if min_sample_size < 1:
        raise ValueError("min_sample_size must be at least one.")
    labeled_rows = [
        (float(row[0]), float(row[1]))
        for row in conn.execute(
            """
            SELECT confidence, outcome_score
            FROM (
                SELECT confidence, outcome_score,
                       ROW_NUMBER() OVER (
                           PARTITION BY decision_id
                           ORDER BY created_at DESC, id DESC
                       ) AS recency_rank
                FROM decision_feedback
                WHERE event_type = 'outcome' AND outcome_score IS NOT NULL
            ) labeled
            WHERE recency_rank = 1
            """
        ).fetchall()
    ]
    sample_size = len(labeled_rows)
    if sample_size < min_sample_size:
        return {
            "status": "insufficient_sample",
            "model_name": MODEL_NAME,
            "model_version": MODEL_VERSION,
            "season": season,
            "sample_size": sample_size,
            "minimum_sample_size": min_sample_size,
            "metrics": None,
        }

    brier_score = sum(
        (confidence - outcome_score) ** 2
        for confidence, outcome_score in labeled_rows
    ) / sample_size
    accuracy = sum(
        (confidence >= 0.5) == (outcome_score >= 0.5)
        for confidence, outcome_score in labeled_rows
    ) / sample_size
    metrics = {
        "schema_version": "decision-calibration-metrics/1.0",
        "brier_score": round(brier_score, 6),
        "accuracy_at_0_5": round(accuracy, 6),
        "expected_calibration_error": round(
            _expected_calibration_error(labeled_rows), 6
        ),
        "mean_confidence": round(
            sum(confidence for confidence, _ in labeled_rows) / sample_size, 6
        ),
        "mean_outcome_score": round(
            sum(outcome for _, outcome in labeled_rows) / sample_size, 6
        ),
        "minimum_sample_size": min_sample_size,
    }
    run_id = DecisionFeedbackRepo(conn).record_calibration(
        model_name=MODEL_NAME,
        model_version=MODEL_VERSION,
        season=season,
        sample_size=sample_size,
        metrics=metrics,
        notes=f"Latest labeled outcome per decision; minimum sample {min_sample_size}.",
    )
    return {
        "status": "available",
        "calibration_run_id": run_id,
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "season": season,
        "sample_size": sample_size,
        "minimum_sample_size": min_sample_size,
        "metrics": metrics,
    }
