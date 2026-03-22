"""Add Phase 4 profiling tables."""

from alembic import op

# revision identifiers, used by Alembic.
revision = "006_phase4_profiling_tables"
down_revision = "005_league_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS manager_profiles (
            id INTEGER PRIMARY KEY,
            league_id VARCHAR NOT NULL,
            roster_id INTEGER NOT NULL,
            computed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            evidence_count INTEGER NOT NULL,
            low_confidence BOOLEAN NOT NULL,
            exploitability_score FLOAT NOT NULL,
            exploitation_primary VARCHAR,
            exploitation_secondary VARCHAR,
            exploitation_evidence VARCHAR NOT NULL,
            roster_summary VARCHAR,
            aggregate_trade_stats VARCHAR NOT NULL,
            UNIQUE (league_id, roster_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS manager_pitch_angles (
            id INTEGER PRIMARY KEY,
            league_id VARCHAR NOT NULL,
            roster_id INTEGER NOT NULL,
            rank INTEGER NOT NULL,
            deal_archetype VARCHAR NOT NULL,
            send_description VARCHAR NOT NULL,
            avoid_description VARCHAR NOT NULL,
            reasoning VARCHAR NOT NULL,
            computed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (league_id, roster_id, rank)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS manager_pitch_angles")
    op.execute("DROP TABLE IF EXISTS manager_profiles")
