"""Phase 12: rookie pick profile tables."""

from alembic import op

revision = "015_rookie_pick_profiles"
down_revision = "014_phase11_lineup_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS draft_pick_selections (
            id              INTEGER PRIMARY KEY,
            league_id       VARCHAR NOT NULL,
            draft_id        VARCHAR NOT NULL,
            roster_id       INTEGER NOT NULL,
            player_id       VARCHAR NOT NULL,
            pick_slot       INTEGER NOT NULL,
            round_number    INTEGER NOT NULL,
            season          INTEGER NOT NULL,
            draft_type      VARCHAR NOT NULL,
            position        VARCHAR,
            archetype_label VARCHAR,
            ingested_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (league_id, draft_id, roster_id, player_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS manager_rookie_pick_profiles (
            id                       INTEGER PRIMARY KEY,
            league_id                VARCHAR NOT NULL,
            roster_id                INTEGER NOT NULL,
            computed_at              TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            pick_premium_score       FLOAT,
            pick_trade_evidence      INTEGER NOT NULL DEFAULT 0,
            draft_selection_count    INTEGER NOT NULL DEFAULT 0,
            positional_tendency_json VARCHAR NOT NULL DEFAULT '{}',
            dominant_archetype       VARCHAR,
            archetype_pattern_json   VARCHAR NOT NULL DEFAULT '{}',
            show_draft_picks_tab     BOOLEAN NOT NULL DEFAULT FALSE,
            UNIQUE (league_id, roster_id)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS manager_rookie_pick_profiles")
    op.execute("DROP TABLE IF EXISTS draft_pick_selections")

