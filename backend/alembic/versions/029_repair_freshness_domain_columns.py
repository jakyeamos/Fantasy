"""Repair freshness-domain columns required by the current context reader."""

from __future__ import annotations

from alembic import op


revision = "029_repair_freshness_domain_columns"
down_revision = "028_decision_followups"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for statement in (
        "ALTER TABLE freshness_domains ADD COLUMN IF NOT EXISTS fetched_at TIMESTAMP",
        "ALTER TABLE freshness_domains ADD COLUMN IF NOT EXISTS observed_at TIMESTAMP",
        "ALTER TABLE freshness_domains ADD COLUMN IF NOT EXISTS effective_at TIMESTAMP",
        "ALTER TABLE freshness_domains ADD COLUMN IF NOT EXISTS coverage_through TIMESTAMP",
        "ALTER TABLE freshness_domains ADD COLUMN IF NOT EXISTS status VARCHAR",
        "ALTER TABLE freshness_domains ADD COLUMN IF NOT EXISTS source_id VARCHAR",
        "ALTER TABLE freshness_domains ADD COLUMN IF NOT EXISTS record_count INTEGER",
    ):
        op.execute(statement)
    op.execute("UPDATE freshness_domains SET status = 'fresh' WHERE status IS NULL")


def downgrade() -> None:
    for column_name in (
        "record_count",
        "source_id",
        "status",
        "coverage_through",
        "effective_at",
        "observed_at",
        "fetched_at",
    ):
        op.execute(f"ALTER TABLE freshness_domains DROP COLUMN IF EXISTS {column_name}")
