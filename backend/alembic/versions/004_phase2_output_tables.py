"""Add Phase 2 intelligence output tables."""

from alembic import op

# revision identifiers, used by Alembic.
revision = "004_phase2_output_tables"
down_revision = "003_add_adp_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS team_scorecards (
            id INTEGER PRIMARY KEY,
            league_id VARCHAR NOT NULL,
            roster_id INTEGER NOT NULL,
            computed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            win_now FLOAT NOT NULL,
            future_value FLOAT NOT NULL,
            depth FLOAT NOT NULL,
            pick_capital FLOAT NOT NULL,
            flexibility FLOAT NOT NULL,
            fragility FLOAT NOT NULL,
            age_risk FLOAT NOT NULL,
            liquidity FLOAT NOT NULL,
            positional_insulation FLOAT NOT NULL,
            composite FLOAT NOT NULL,
            computation_json VARCHAR,
            UNIQUE (league_id, roster_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS team_directions (
            id INTEGER PRIMARY KEY,
            league_id VARCHAR NOT NULL,
            roster_id INTEGER NOT NULL,
            computed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            primary_label VARCHAR NOT NULL,
            confidence FLOAT NOT NULL,
            reasoning VARCHAR NOT NULL,
            alternates_json VARCHAR NOT NULL,
            delta_json VARCHAR NOT NULL,
            approved_moves VARCHAR NOT NULL,
            discouraged_moves VARCHAR NOT NULL,
            UNIQUE (league_id, roster_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS player_values (
            id INTEGER PRIMARY KEY,
            league_id VARCHAR NOT NULL,
            roster_id INTEGER NOT NULL,
            player_id VARCHAR NOT NULL,
            computed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            comp_current_production FLOAT,
            comp_short_term FLOAT,
            comp_role_stability FLOAT,
            comp_age_curve FLOAT,
            comp_insulation FLOAT,
            comp_market_liquidity FLOAT,
            comp_positional_scarcity FLOAT,
            comp_fragility FLOAT,
            comp_ceiling FLOAT,
            comp_floor FLOAT,
            comp_rerollability FLOAT,
            comp_contract FLOAT,
            lens_production FLOAT,
            lens_market FLOAT,
            lens_insulation FLOAT,
            lens_team_fit FLOAT,
            lens_direction FLOAT,
            UNIQUE (league_id, roster_id, player_id)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS player_values")
    op.execute("DROP TABLE IF EXISTS team_directions")
    op.execute("DROP TABLE IF EXISTS team_scorecards")
