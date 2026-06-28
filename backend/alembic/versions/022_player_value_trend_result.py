"""Persist trend results on player valuations."""

from __future__ import annotations

from alembic import op

revision = "022_player_value_trend_result"
down_revision = ("021_player_trends", "021_recommendation_phase")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE player_values ADD COLUMN IF NOT EXISTS trend_result_json VARCHAR")


def downgrade() -> None:
    op.execute("ALTER TABLE player_values DROP COLUMN IF EXISTS trend_result_json")
