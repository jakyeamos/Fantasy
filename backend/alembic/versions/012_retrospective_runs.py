"""Create retrospective_runs table for post-season recalibration tracking."""

from alembic import op

revision = "012_retrospective_runs"
down_revision = "011_draft_slots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS retrospective_runs (
            id INTEGER PRIMARY KEY,
            run_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            run_type VARCHAR NOT NULL,
            season VARCHAR NOT NULL,
            grades_json VARCHAR NOT NULL,
            notes VARCHAR
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS retrospective_runs")
