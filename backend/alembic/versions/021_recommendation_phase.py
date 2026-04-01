"""Phase 17: recommendation market intelligence schema."""

from __future__ import annotations

from alembic import op

revision = "021_recommendation_phase"
down_revision = "020_expand_prospect_feature_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS player_context_flags (
            id            INTEGER PRIMARY KEY,
            player_id     VARCHAR NOT NULL,
            flag_type     VARCHAR NOT NULL,
            created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at    TIMESTAMP,
            source        VARCHAR NOT NULL DEFAULT 'sleeper_ingest',
            metadata_json VARCHAR,
            UNIQUE (player_id, flag_type)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS market_values (
            id                  INTEGER PRIMARY KEY,
            player_id           VARCHAR NOT NULL,
            fetched_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            fantasycalc_value   FLOAT,
            fantasycalc_rank    INTEGER,
            fantasycalc_trend30 FLOAT,
            adp_baseline        FLOAT,
            UNIQUE (player_id)
        )
        """
    )
    op.execute("ALTER TABLE players ADD COLUMN IF NOT EXISTS mfl_id VARCHAR DEFAULT NULL")
    op.execute(
        "ALTER TABLE lineup_scores ADD COLUMN IF NOT EXISTS recommendation_cards_json VARCHAR DEFAULT '[]'"
    )
    op.execute(
        "ALTER TABLE hygiene_suggestions ADD COLUMN IF NOT EXISTS recommendation_cards_json VARCHAR DEFAULT '[]'"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS market_values")
    op.execute("DROP TABLE IF EXISTS player_context_flags")
    op.execute("ALTER TABLE players DROP COLUMN IF EXISTS mfl_id")
    op.execute("ALTER TABLE lineup_scores DROP COLUMN IF EXISTS recommendation_cards_json")
    op.execute("ALTER TABLE hygiene_suggestions DROP COLUMN IF EXISTS recommendation_cards_json")
