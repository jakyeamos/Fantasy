"""Add append-only agent decision feedback and calibration evidence."""

from __future__ import annotations

from alembic import op

revision = "025_agent_decision_feedback"
down_revision = "024_team_context_by_season"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS decision_feedback (
            id                    INTEGER PRIMARY KEY,
            decision_id           VARCHAR NOT NULL,
            created_at            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            league_id             VARCHAR NOT NULL,
            roster_id             INTEGER NOT NULL,
            packet_version        VARCHAR NOT NULL,
            recommendation_action VARCHAR NOT NULL,
            confidence            DOUBLE NOT NULL,
            action_taken          VARCHAR,
            outcome               VARCHAR,
            notes                 VARCHAR,
            packet_json           VARCHAR NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS decision_calibration_runs (
            id            INTEGER PRIMARY KEY,
            run_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            model_name    VARCHAR NOT NULL,
            model_version VARCHAR NOT NULL,
            season        VARCHAR NOT NULL,
            sample_size   INTEGER NOT NULL,
            metrics_json  VARCHAR NOT NULL,
            notes         VARCHAR
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS decision_calibration_runs")
    op.execute("DROP TABLE IF EXISTS decision_feedback")
