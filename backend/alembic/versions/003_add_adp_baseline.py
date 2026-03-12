"""Add player_adp_baseline table."""

from alembic import op

# revision identifiers, used by Alembic.
revision = "003_add_adp_baseline"
down_revision = "002_add_player_stats_weekly"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS player_adp_baseline (
            player_id VARCHAR,
            player_name VARCHAR,
            position VARCHAR,
            adp DOUBLE,
            adp_source VARCHAR,
            loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS player_adp_baseline")
