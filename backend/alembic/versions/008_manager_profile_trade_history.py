"""Persist manager trade history in cached profiles."""

from alembic import op

# revision identifiers, used by Alembic.
revision = "008_manager_profile_trade_history"
down_revision = "007_roster_owner_display_name"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE manager_profiles
        ADD COLUMN trade_history VARCHAR NOT NULL DEFAULT '[]'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE manager_profiles
        DROP COLUMN trade_history
        """
    )
