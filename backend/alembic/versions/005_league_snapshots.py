"""Add Phase 3 league snapshots table."""

from alembic import op

# revision identifiers, used by Alembic.
revision = "005_league_snapshots"
down_revision = "004_phase2_output_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS league_snapshots (
            id INTEGER PRIMARY KEY,
            league_id VARCHAR NOT NULL,
            snapshot_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            snapshot_type VARCHAR NOT NULL,
            triggered_by VARCHAR NOT NULL,
            ingest_run_id INTEGER,
            payload_json VARCHAR NOT NULL,
            base_snapshot_id INTEGER
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS league_snapshots")
