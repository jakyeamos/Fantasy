"""Initial DuckDB schema for phase 1."""

from alembic import op

# revision identifiers, used by Alembic.
revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    statements = [
        """
        CREATE TABLE IF NOT EXISTS leagues (
            league_id VARCHAR PRIMARY KEY,
            name VARCHAR NOT NULL,
            season VARCHAR NOT NULL,
            scoring_settings VARCHAR NOT NULL,
            roster_positions VARCHAR NOT NULL,
            settings_blob VARCHAR,
            superflex BOOLEAN NOT NULL DEFAULT FALSE,
            tep BOOLEAN NOT NULL DEFAULT FALSE,
            ppr DOUBLE NOT NULL DEFAULT 0.0,
            ingested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS rosters (
            id INTEGER PRIMARY KEY,
            league_id VARCHAR NOT NULL,
            roster_id INTEGER NOT NULL,
            owner_id VARCHAR,
            starters VARCHAR NOT NULL,
            players VARCHAR NOT NULL,
            reserve VARCHAR,
            taxi VARCHAR,
            ingested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (league_id, roster_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS standings (
            id INTEGER PRIMARY KEY,
            league_id VARCHAR NOT NULL,
            roster_id INTEGER NOT NULL,
            wins INTEGER NOT NULL DEFAULT 0,
            losses INTEGER NOT NULL DEFAULT 0,
            ties INTEGER NOT NULL DEFAULT 0,
            fpts DOUBLE NOT NULL DEFAULT 0.0,
            fpts_against DOUBLE NOT NULL DEFAULT 0.0,
            ingested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (league_id, roster_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS traded_picks (
            id INTEGER PRIMARY KEY,
            league_id VARCHAR NOT NULL,
            season VARCHAR NOT NULL,
            round INTEGER NOT NULL,
            roster_id INTEGER NOT NULL,
            owner_id VARCHAR NOT NULL,
            previous_owner_id VARCHAR,
            ingested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (league_id, season, round, roster_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id VARCHAR PRIMARY KEY,
            league_id VARCHAR NOT NULL,
            type VARCHAR NOT NULL,
            status VARCHAR NOT NULL,
            created_at TIMESTAMP,
            roster_ids VARCHAR,
            adds VARCHAR,
            drops VARCHAR,
            draft_picks VARCHAR,
            week INTEGER,
            ingested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS players (
            player_id VARCHAR PRIMARY KEY,
            full_name VARCHAR,
            position VARCHAR,
            team VARCHAR,
            age INTEGER,
            metadata_blob VARCHAR,
            refreshed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS ingest_runs (
            id INTEGER PRIMARY KEY,
            league_id VARCHAR NOT NULL,
            run_type VARCHAR NOT NULL,
            status VARCHAR NOT NULL,
            started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            cursor_json VARCHAR,
            gaps_json VARCHAR,
            error_message VARCHAR
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS corrections (
            id INTEGER PRIMARY KEY,
            league_id VARCHAR NOT NULL,
            entity_type VARCHAR NOT NULL,
            entity_id VARCHAR NOT NULL,
            field VARCHAR NOT NULL,
            original_value VARCHAR,
            corrected_value VARCHAR NOT NULL,
            corrected_by VARCHAR NOT NULL DEFAULT 'user',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (league_id, entity_type, entity_id, field)
        )
        """,
    ]

    for statement in statements:
        op.execute(statement)


def downgrade() -> None:
    for table_name in [
        "corrections",
        "ingest_runs",
        "players",
        "transactions",
        "traded_picks",
        "standings",
        "rosters",
        "leagues",
    ]:
        op.execute(f"DROP TABLE IF EXISTS {table_name}")
