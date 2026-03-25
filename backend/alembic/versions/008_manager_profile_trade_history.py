"""Persist manager trade history in cached profiles."""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "008_manager_profile_trade_history"
down_revision = "007_roster_owner_display_name"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    exists = bind.execute(
        sa.text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'manager_profiles'
              AND column_name = 'trade_history'
            LIMIT 1
            """
        )
    ).fetchone()
    if not exists:
        op.execute(
            """
            ALTER TABLE manager_profiles
            ADD COLUMN trade_history VARCHAR
            """
        )
    op.execute(
        """
        UPDATE manager_profiles
        SET trade_history = '[]'
        WHERE trade_history IS NULL
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    exists = bind.execute(
        sa.text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'manager_profiles'
              AND column_name = 'trade_history'
            LIMIT 1
            """
        )
    ).fetchone()
    if exists:
        op.execute(
            """
            ALTER TABLE manager_profiles
            DROP COLUMN trade_history
            """
        )
