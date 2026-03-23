"""Add owner display names to rosters."""

from alembic import op

# revision identifiers, used by Alembic.
revision = "007_roster_owner_display_name"
down_revision = "006_phase4_profiling_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE rosters
        ADD COLUMN owner_display_name VARCHAR
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE rosters
        DROP COLUMN owner_display_name
        """
    )
