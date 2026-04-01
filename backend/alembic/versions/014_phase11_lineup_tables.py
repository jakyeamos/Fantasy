"""Phase 11: lineup intelligence tables (taxi config, lineup scores, hygiene)."""

from alembic import op

revision = "014_phase11_lineup_tables"
down_revision = "013_draft_order_rules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS league_taxi_configs (
            id                     INTEGER PRIMARY KEY,
            league_id              VARCHAR NOT NULL UNIQUE,
            taxi_slots             INTEGER NOT NULL,
            taxi_years_eligible    INTEGER NOT NULL,
            years_pro_cutoff       INTEGER NOT NULL,
            manual_exceptions_json VARCHAR NOT NULL DEFAULT '[]',
            created_at             TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at             TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS lineup_scores (
            id                      INTEGER PRIMARY KEY,
            league_id               VARCHAR NOT NULL,
            roster_id               INTEGER NOT NULL,
            computed_at             TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            total_lineup_score      FLOAT NOT NULL,
            title_window_label      VARCHAR NOT NULL,
            title_window_composite  FLOAT NOT NULL,
            ceiling_score           FLOAT NOT NULL,
            stability_score         FLOAT NOT NULL,
            depth_score             FLOAT NOT NULL,
            slot_scores_json        VARCHAR NOT NULL,
            UNIQUE (league_id, roster_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS hygiene_suggestions (
            id                      INTEGER PRIMARY KEY,
            league_id               VARCHAR NOT NULL,
            roster_id               INTEGER NOT NULL,
            computed_at             TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            suggestions_json        VARCHAR NOT NULL,
            UNIQUE (league_id, roster_id)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS hygiene_suggestions")
    op.execute("DROP TABLE IF EXISTS lineup_scores")
    op.execute("DROP TABLE IF EXISTS league_taxi_configs")
