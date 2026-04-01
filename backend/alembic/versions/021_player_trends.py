"""Add player trend storage for Phase 21."""

from alembic import op

# revision identifiers, used by Alembic.
revision = "021_player_trends"
down_revision = "020_expand_prospect_feature_columns"
branch_labels = None
depends_on = None


PLAYER_TRENDS_DDL = """
CREATE TABLE IF NOT EXISTS player_trends (
    id                       INTEGER PRIMARY KEY,
    player_id                VARCHAR NOT NULL,
    season                   INTEGER NOT NULL,
    trend_label              VARCHAR,
    confidence               VARCHAR,
    delta_magnitude          FLOAT,
    adp_delta                FLOAT,
    comp_current_production  FLOAT,
    comp_short_term          FLOAT,
    comp_role_stability      FLOAT,
    comp_age_curve           FLOAT,
    comp_insulation          FLOAT,
    comp_market_liquidity    FLOAT,
    comp_positional_scarcity FLOAT,
    comp_fragility           FLOAT,
    comp_ceiling             FLOAT,
    comp_floor               FLOAT,
    comp_rerollability       FLOAT,
    comp_contract            FLOAT,
    startup_adp              FLOAT,
    backfilled               BOOLEAN NOT NULL DEFAULT FALSE,
    computed_at              TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (player_id, season)
)
"""


def upgrade() -> None:
    op.execute(PLAYER_TRENDS_DDL)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS player_trends")
