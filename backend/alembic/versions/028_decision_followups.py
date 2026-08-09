"""Add append-only decision follow-up scheduling and resolution state."""

from __future__ import annotations

from alembic import op

revision = "028_decision_followups"
down_revision = "027_market_refresh_provenance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE decision_feedback ADD COLUMN IF NOT EXISTS follow_up_at TIMESTAMP"
    )
    op.execute(
        "ALTER TABLE decision_feedback ADD COLUMN IF NOT EXISTS resolution_state "
        "VARCHAR DEFAULT 'awaiting_action'"
    )
    op.execute(
        """
        UPDATE decision_feedback
        SET resolution_state = CASE
            WHEN event_type = 'outcome' THEN 'resolved'
            WHEN event_type IN ('accepted', 'rejected', 'completed') THEN 'awaiting_outcome'
            ELSE 'awaiting_action'
        END
        """
    )
    op.execute(
        """
        UPDATE decision_feedback
        SET follow_up_at = created_at + INTERVAL 30 DAY
        WHERE resolution_state != 'resolved' AND follow_up_at IS NULL
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE decision_feedback DROP COLUMN IF EXISTS resolution_state")
    op.execute("ALTER TABLE decision_feedback DROP COLUMN IF EXISTS follow_up_at")
