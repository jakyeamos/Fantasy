"""Create rookie board cache and league draft tendencies tables."""

from alembic import op

# revision identifiers, used by Alembic.
revision = "010_rookie_board"
down_revision = "009_pick_values"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS rookie_board_cache (
            id INTEGER PRIMARY KEY,
            league_id VARCHAR NOT NULL,
            computed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            class_strength_signal FLOAT NOT NULL,
            board_json VARCHAR NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS league_draft_tendencies (
            id INTEGER PRIMARY KEY,
            league_id VARCHAR NOT NULL,
            computed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            tendency_type VARCHAR NOT NULL,
            position VARCHAR,
            player_id VARCHAR,
            player_name VARCHAR,
            early_draft_slots FLOAT,
            adp_delta FLOAT,
            system_value_slot INTEGER
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS league_draft_tendencies")
    op.execute("DROP TABLE IF EXISTS rookie_board_cache")
