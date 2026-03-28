"""Phase 14: trust infrastructure acknowledgment table."""

from alembic import op

revision = "019_trust_infrastructure"
down_revision = "018_waiver_startup_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS league_format_acknowledgments (
            id                  INTEGER PRIMARY KEY,
            league_id           VARCHAR NOT NULL UNIQUE,
            acknowledged_rules  VARCHAR NOT NULL,
            acknowledged_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS league_format_acknowledgments")
