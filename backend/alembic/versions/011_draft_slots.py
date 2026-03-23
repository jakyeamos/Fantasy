"""Create draft_slots table to store confirmed pick order from Sleeper draft objects."""

from alembic import op

revision = "011_draft_slots"
down_revision = "010_rookie_board"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS draft_slots (
            id              INTEGER PRIMARY KEY,
            league_id       VARCHAR NOT NULL,
            draft_id        VARCHAR NOT NULL,
            season          INTEGER NOT NULL,
            roster_id       INTEGER NOT NULL,
            confirmed_slot  INTEGER NOT NULL,
            status          VARCHAR NOT NULL,
            ingested_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (league_id, draft_id, roster_id)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS draft_slots")
