"""Phase 13: context awareness tables."""

from alembic import op

revision = "016_context_awareness"
down_revision = "015_rookie_pick_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS calendar_overrides (
            id         INTEGER PRIMARY KEY,
            league_id  VARCHAR NOT NULL UNIQUE,
            state      VARCHAR NOT NULL,
            set_by     VARCHAR NOT NULL DEFAULT 'user',
            set_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS freshness_domains (
            id           INTEGER PRIMARY KEY,
            league_id    VARCHAR NOT NULL,
            domain       VARCHAR NOT NULL,
            last_updated TIMESTAMP,
            notes        VARCHAR,
            UNIQUE (league_id, domain)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS freshness_domains")
    op.execute("DROP TABLE IF EXISTS calendar_overrides")
