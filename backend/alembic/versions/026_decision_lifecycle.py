"""Add structured lifecycle events for agent decisions."""

from __future__ import annotations

from alembic import op

revision = "026_decision_lifecycle"
down_revision = "025_agent_decision_feedback"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE decision_feedback ADD COLUMN IF NOT EXISTS event_type VARCHAR DEFAULT 'feedback'"
    )
    op.execute(
        "ALTER TABLE decision_feedback ADD COLUMN IF NOT EXISTS outcome_score DOUBLE DEFAULT NULL"
    )
    op.execute(
        "UPDATE decision_feedback SET event_type = 'outcome' WHERE outcome IS NOT NULL AND event_type = 'feedback'"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE decision_feedback DROP COLUMN IF EXISTS outcome_score")
    op.execute("ALTER TABLE decision_feedback DROP COLUMN IF EXISTS event_type")
