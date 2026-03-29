"""Phase 15: waiver/startup workflow tables and schema extensions."""

from __future__ import annotations

import logging

from alembic import op

logger = logging.getLogger(__name__)

revision = "018_waiver_startup_tables"
down_revision = "017_prospect_lab_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE rosters ADD COLUMN IF NOT EXISTS waiver_position INTEGER")
    op.execute("ALTER TABLE rosters ADD COLUMN IF NOT EXISTS waiver_budget_used INTEGER")
    op.execute("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS waiver_bid INTEGER")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS waiver_recommendations (
            id                  INTEGER PRIMARY KEY,
            league_id           VARCHAR NOT NULL,
            roster_id           INTEGER NOT NULL,
            computed_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            recommendations_json VARCHAR NOT NULL,
            UNIQUE (league_id, roster_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS startup_contexts (
            id                  INTEGER PRIMARY KEY,
            league_id           VARCHAR NOT NULL UNIQUE,
            computed_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            draft_status        VARCHAR NOT NULL,
            build_template      VARCHAR NOT NULL,
            context_json        VARCHAR NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS orphan_intakes (
            id                       INTEGER PRIMARY KEY,
            league_id                VARCHAR NOT NULL,
            roster_id                INTEGER NOT NULL,
            computed_at              TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            age_curve_score          FLOAT NOT NULL,
            pick_capital_score       FLOAT NOT NULL,
            dead_spots_score         FLOAT NOT NULL,
            lineup_viability_score   FLOAT NOT NULL,
            liquidation_score        FLOAT NOT NULL,
            composite_score          FLOAT NOT NULL,
            intake_json              VARCHAR NOT NULL,
            UNIQUE (league_id, roster_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS action_plans (
            id           INTEGER PRIMARY KEY,
            league_id    VARCHAR NOT NULL,
            roster_id    INTEGER NOT NULL,
            computed_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            plan_type    VARCHAR NOT NULL,
            items_json   VARCHAR NOT NULL,
            summary      VARCHAR NOT NULL,
            UNIQUE (league_id, roster_id)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS action_plans")
    op.execute("DROP TABLE IF EXISTS orphan_intakes")
    op.execute("DROP TABLE IF EXISTS startup_contexts")
    op.execute("DROP TABLE IF EXISTS waiver_recommendations")
    logger.warning(
        "DuckDB downgrade for %s leaves rosters.waiver_* and transactions.waiver_bid in place.",
        revision,
    )
