"""Add curated team context source."""

from __future__ import annotations

from alembic import op

revision = "024_team_context_by_season"
down_revision = "023_weekly_team_context"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS team_context_by_season (
            team                  VARCHAR NOT NULL,
            season                INTEGER NOT NULL,
            head_coach            VARCHAR,
            offensive_coordinator VARCHAR,
            play_caller           VARCHAR,
            offensive_system      VARCHAR,
            pace_label            VARCHAR,
            pass_rate_label       VARCHAR,
            source                VARCHAR NOT NULL DEFAULT 'manual_csv',
            notes                 VARCHAR,
            loaded_at             TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (team, season)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS team_context_by_season")
