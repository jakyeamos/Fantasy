from sqlalchemy import (
    Boolean,
    Column,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    TIMESTAMP,
    UniqueConstraint,
    text,
)

metadata = MetaData()

leagues = Table(
    "leagues",
    metadata,
    Column("league_id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("season", String, nullable=False),
    Column("scoring_settings", String, nullable=False),
    Column("roster_positions", String, nullable=False),
    Column("settings_blob", String),
    Column("superflex", Boolean, nullable=False, server_default=text("FALSE")),
    Column("tep", Boolean, nullable=False, server_default=text("FALSE")),
    Column("ppr", Float, nullable=False, server_default=text("0.0")),
    Column("ingested_at", TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
)

rosters = Table(
    "rosters",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("league_id", String, nullable=False),
    Column("roster_id", Integer, nullable=False),
    Column("owner_id", String),
    Column("owner_display_name", String),
    Column("starters", String, nullable=False),
    Column("players", String, nullable=False),
    Column("reserve", String),
    Column("taxi", String),
    Column("ingested_at", TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    UniqueConstraint("league_id", "roster_id", name="uq_rosters_league_roster"),
)

standings = Table(
    "standings",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("league_id", String, nullable=False),
    Column("roster_id", Integer, nullable=False),
    Column("wins", Integer, nullable=False, server_default=text("0")),
    Column("losses", Integer, nullable=False, server_default=text("0")),
    Column("ties", Integer, nullable=False, server_default=text("0")),
    Column("fpts", Float, nullable=False, server_default=text("0.0")),
    Column("fpts_against", Float, nullable=False, server_default=text("0.0")),
    Column("ingested_at", TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    UniqueConstraint("league_id", "roster_id", name="uq_standings_league_roster"),
)

draft_slots = Table(
    "draft_slots",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("league_id", String, nullable=False),
    Column("draft_id", String, nullable=False),
    Column("season", Integer, nullable=False),
    Column("roster_id", Integer, nullable=False),
    Column("confirmed_slot", Integer, nullable=False),
    Column("status", String, nullable=False),
    Column("ingested_at", TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    UniqueConstraint("league_id", "draft_id", "roster_id", name="uq_draft_slots_identity"),
)

traded_picks = Table(
    "traded_picks",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("league_id", String, nullable=False),
    Column("season", String, nullable=False),
    Column("round", Integer, nullable=False),
    Column("roster_id", Integer, nullable=False),
    Column("owner_id", String, nullable=False),
    Column("previous_owner_id", String),
    Column("ingested_at", TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    UniqueConstraint("league_id", "season", "round", "roster_id", name="uq_traded_picks_identity"),
)

transactions = Table(
    "transactions",
    metadata,
    Column("transaction_id", String, primary_key=True),
    Column("league_id", String, nullable=False),
    Column("type", String, nullable=False),
    Column("status", String, nullable=False),
    Column("created_at", TIMESTAMP),
    Column("roster_ids", String),
    Column("adds", String),
    Column("drops", String),
    Column("draft_picks", String),
    Column("week", Integer),
    Column("ingested_at", TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
)

players = Table(
    "players",
    metadata,
    Column("player_id", String, primary_key=True),
    Column("full_name", String),
    Column("position", String),
    Column("team", String),
    Column("age", Integer),
    Column("metadata_blob", String),
    Column("refreshed_at", TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
)

ingest_runs = Table(
    "ingest_runs",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("league_id", String, nullable=False),
    Column("run_type", String, nullable=False),
    Column("status", String, nullable=False),
    Column("started_at", TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    Column("completed_at", TIMESTAMP),
    Column("cursor_json", String),
    Column("gaps_json", String),
    Column("error_message", String),
)

corrections = Table(
    "corrections",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("league_id", String, nullable=False),
    Column("entity_type", String, nullable=False),
    Column("entity_id", String, nullable=False),
    Column("field", String, nullable=False),
    Column("original_value", String),
    Column("corrected_value", String, nullable=False),
    Column("corrected_by", String, nullable=False, server_default=text("'user'")),
    Column("created_at", TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    UniqueConstraint("league_id", "entity_type", "entity_id", "field", name="uq_corrections_identity"),
)

player_stats_weekly = Table(
    "player_stats_weekly",
    metadata,
    Column("player_id", String, nullable=False),
    Column("player_name", String),
    Column("position", String),
    Column("season", Integer, nullable=False),
    Column("week", Integer, nullable=False),
    Column("receptions", Float),
    Column("targets", Float),
    Column("receiving_yards", Float),
    Column("receiving_tds", Float),
    Column("rushing_yards", Float),
    Column("rushing_tds", Float),
    Column("carries", Float),
    Column("passing_yards", Float),
    Column("passing_tds", Float),
    Column("interceptions", Float),
    Column("passing_2pt_conversions", Float),
    Column("receiving_2pt_conversions", Float),
    Column("rushing_2pt_conversions", Float),
    Column("fantasy_points", Float),
    UniqueConstraint("player_id", "season", "week", name="uq_player_stats_weekly_identity"),
)

player_adp_baseline = Table(
    "player_adp_baseline",
    metadata,
    Column("player_id", String),
    Column("player_name", String),
    Column("position", String),
    Column("adp", Float),
    Column("adp_source", String),
    Column("loaded_at", TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
)

__all__ = [
    "metadata",
    "leagues",
    "rosters",
    "standings",
    "traded_picks",
    "transactions",
    "players",
    "ingest_runs",
    "corrections",
    "player_stats_weekly",
    "player_adp_baseline",
]
