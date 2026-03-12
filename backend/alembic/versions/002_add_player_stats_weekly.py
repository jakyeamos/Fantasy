"""Add player_stats_weekly table."""

from alembic import op

# revision identifiers, used by Alembic.
revision = "002_add_player_stats_weekly"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS player_stats_weekly (
            player_id VARCHAR NOT NULL,
            player_name VARCHAR,
            position VARCHAR,
            season INTEGER NOT NULL,
            week INTEGER NOT NULL,
            receptions DOUBLE,
            targets DOUBLE,
            receiving_yards DOUBLE,
            receiving_tds DOUBLE,
            rushing_yards DOUBLE,
            rushing_tds DOUBLE,
            carries DOUBLE,
            passing_yards DOUBLE,
            passing_tds DOUBLE,
            interceptions DOUBLE,
            passing_2pt_conversions DOUBLE,
            receiving_2pt_conversions DOUBLE,
            rushing_2pt_conversions DOUBLE,
            fantasy_points DOUBLE,
            UNIQUE (player_id, season, week)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS player_stats_weekly")
