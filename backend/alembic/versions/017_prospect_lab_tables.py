"""Create Phase 8 historical prospect lab tables."""

from alembic import op

# revision identifiers, used by Alembic.
revision = "017_prospect_lab_tables"
down_revision = "016_context_awareness"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS historical_prospect_features (
            player_id VARCHAR NOT NULL,
            draft_year INTEGER NOT NULL,
            position VARCHAR NOT NULL,
            player_name VARCHAR,
            age_at_draft DOUBLE,
            draft_ovr INTEGER,
            forty DOUBLE,
            weight DOUBLE,
            height DOUBLE,
            vertical DOUBLE,
            bench INTEGER,
            cone DOUBLE,
            shuttle DOUBLE,
            college_rec_ypg DOUBLE,
            college_rush_ypg DOUBLE,
            college_mkt_share_proxy DOUBLE,
            college_td_rate DOUBLE,
            college_completion_pct_proxy DOUBLE,
            adp DOUBLE,
            archetype_label VARCHAR,
            outcome_bucket VARCHAR,
            PRIMARY KEY (player_id, draft_year)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS prospect_model_outputs (
            league_id VARCHAR NOT NULL,
            draft_season INTEGER NOT NULL,
            player_id VARCHAR NOT NULL,
            player_name VARCHAR NOT NULL,
            position VARCHAR NOT NULL,
            archetype_label VARCHAR NOT NULL,
            hit_rate_bucket VARCHAR NOT NULL,
            tier INTEGER NOT NULL,
            predicted_tier INTEGER NOT NULL,
            predicted_bucket VARCHAR NOT NULL,
            risk_band VARCHAR NOT NULL,
            overvalue_flag_direction VARCHAR,
            overvalue_magnitude INTEGER,
            low_confidence BOOLEAN NOT NULL DEFAULT FALSE,
            comps_json VARCHAR NOT NULL DEFAULT '[]',
            computed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (league_id, draft_season, player_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS prospect_sub_flags (
            id INTEGER PRIMARY KEY,
            league_id VARCHAR NOT NULL,
            player_id VARCHAR NOT NULL,
            signal_name VARCHAR NOT NULL,
            direction VARCHAR NOT NULL,
            magnitude_str VARCHAR NOT NULL
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS prospect_sub_flags")
    op.execute("DROP TABLE IF EXISTS prospect_model_outputs")
    op.execute("DROP TABLE IF EXISTS historical_prospect_features")
