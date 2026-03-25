"""Create league_draft_order_rules table for Phase 10 draft-order configuration."""

from alembic import op

revision = "013_draft_order_rules"
down_revision = "012_retrospective_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS league_draft_order_rules (
            id                INTEGER PRIMARY KEY,
            league_id         VARCHAR NOT NULL UNIQUE,
            non_playoff_basis VARCHAR NOT NULL,
            playoff_ordering  VARCHAR NOT NULL,
            tiebreaker        VARCHAR NOT NULL,
            created_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS league_draft_order_rules")
