"""Add weekly public team schedule context."""

from __future__ import annotations

from alembic import op

revision = "023_weekly_team_context"
down_revision = "022_player_value_trend_result"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS team_schedule_weekly (
            team       VARCHAR NOT NULL,
            season     INTEGER NOT NULL,
            week       INTEGER NOT NULL,
            opponent   VARCHAR,
            is_home    BOOLEAN NOT NULL DEFAULT FALSE,
            game_date  VARCHAR,
            game_type  VARCHAR,
            loaded_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (team, season, week)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS team_schedule_weekly")
