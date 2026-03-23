"""Create pick_values table for Phase 6 dynamic pick valuation output.

Note: Plan 06-01 referenced this as 007 but migrations 007 and 008 already exist.
Using 009 as the correct next sequence number.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "009_pick_values"
down_revision = "008_manager_profile_trade_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS pick_values (
            id                      INTEGER PRIMARY KEY,
            league_id               VARCHAR NOT NULL,
            pick_owner_roster_id    INTEGER NOT NULL,
            pick_year               INTEGER NOT NULL,
            pick_round              INTEGER NOT NULL,
            computed_at             TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expected_draft_slot     FLOAT NOT NULL,
            base_value              FLOAT NOT NULL,
            timed_value             FLOAT NOT NULL,
            league_adjusted_value   FLOAT NOT NULL,
            demand_adjusted_value   FLOAT NOT NULL,
            timing_label            VARCHAR NOT NULL,
            timing_reasoning        VARCHAR NOT NULL,
            class_strength_signal   FLOAT NOT NULL DEFAULT 0.0,
            years_out               INTEGER NOT NULL DEFAULT 0,
            computation_json        VARCHAR,
            UNIQUE (league_id, pick_owner_roster_id, pick_year, pick_round)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS pick_values")
