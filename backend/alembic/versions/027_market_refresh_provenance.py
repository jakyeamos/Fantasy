"""Persist external market refresh provenance and quality."""

from __future__ import annotations

from alembic import op

revision = "027_market_refresh_provenance"
down_revision = "026_decision_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS market_refresh_runs (
            id                  INTEGER PRIMARY KEY,
            run_at              TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            source              VARCHAR NOT NULL,
            num_qbs             INTEGER NOT NULL,
            num_teams           INTEGER NOT NULL,
            ppr                 DOUBLE NOT NULL,
            status              VARCHAR NOT NULL,
            source_rows         INTEGER,
            matched_rows        INTEGER,
            matched_unique_rows INTEGER,
            unmatched_rows      INTEGER,
            market_value_rows   INTEGER,
            coverage_ratio      DOUBLE,
            error_detail        VARCHAR
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS market_refresh_runs")
