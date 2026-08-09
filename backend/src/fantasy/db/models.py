from sqlalchemy import (
    Boolean,
    Column,
    Date,
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

team_schedule_weekly = Table(
    "team_schedule_weekly",
    metadata,
    Column("team", String, nullable=False),
    Column("season", Integer, nullable=False),
    Column("week", Integer, nullable=False),
    Column("opponent", String),
    Column("is_home", Boolean, nullable=False, server_default=text("FALSE")),
    Column("game_date", String),
    Column("game_type", String),
    Column("loaded_at", TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    UniqueConstraint("team", "season", "week", name="uq_team_schedule_weekly_identity"),
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

team_context_by_season = Table(
    "team_context_by_season",
    metadata,
    Column("team", String, nullable=False),
    Column("season", Integer, nullable=False),
    Column("head_coach", String),
    Column("offensive_coordinator", String),
    Column("play_caller", String),
    Column("offensive_system", String),
    Column("pace_label", String),
    Column("pass_rate_label", String),
    Column("source", String, nullable=False, server_default=text("'manual_csv'")),
    Column("notes", String),
    Column("loaded_at", TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    UniqueConstraint("team", "season", name="uq_team_context_by_season_identity"),
)

freshness_domains = Table(
    "freshness_domains", metadata,
    Column("id", Integer, primary_key=True), Column("league_id", String, nullable=False),
    Column("domain", String, nullable=False), Column("last_updated", TIMESTAMP),
    Column("notes", String), Column("fetched_at", TIMESTAMP), Column("observed_at", TIMESTAMP),
    Column("effective_at", TIMESTAMP), Column("coverage_through", TIMESTAMP),
    Column("status", String, nullable=False, server_default=text("'fresh'")),
    Column("source_id", String), Column("record_count", Integer),
    UniqueConstraint("league_id", "domain", name="uq_freshness_domains_identity"),
)

intelligence_source_runs = Table(
    "intelligence_source_runs", metadata,
    Column("run_id", String, primary_key=True), Column("trigger", String, nullable=False),
    Column("status", String, nullable=False),
    Column("started_at", TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    Column("completed_at", TIMESTAMP), Column("source_outcomes_json", String, nullable=False),
    Column("event_count", Integer, nullable=False, server_default=text("0")),
    Column("impact_count", Integer, nullable=False, server_default=text("0")),
    Column("brief_id", String), Column("error_message", String),
)

source_observations = Table(
    "source_observations", metadata,
    Column("observation_id", String, primary_key=True), Column("run_id", String, nullable=False),
    Column("source_id", String, nullable=False), Column("source_tier", String, nullable=False),
    Column("url", String), Column("fetched_at", TIMESTAMP, nullable=False),
    Column("observed_at", TIMESTAMP), Column("effective_at", TIMESTAMP),
    Column("coverage_through", TIMESTAMP), Column("content_hash", String, nullable=False),
    Column("parse_status", String, nullable=False), Column("evidence_excerpt", String),
    Column("payload_json", String, nullable=False),
    Column("authoritative", Boolean, nullable=False, server_default=text("FALSE")),
    Column("model_extracted", Boolean, nullable=False, server_default=text("FALSE")),
    UniqueConstraint("source_id", "content_hash", name="uq_source_observations_hash"),
)

football_events = Table(
    "football_events", metadata,
    Column("event_id", String, primary_key=True), Column("fingerprint", String, nullable=False, unique=True),
    Column("subject_key", String, nullable=False), Column("event_type", String, nullable=False),
    Column("player_id", String), Column("player_name", String), Column("team", String),
    Column("effective_at", TIMESTAMP), Column("observed_at", TIMESTAMP, nullable=False),
    Column("expires_at", TIMESTAMP), Column("verification_state", String, nullable=False),
    Column("confidence", Float, nullable=False), Column("summary", String, nullable=False),
    Column("details_json", String, nullable=False),
    Column("created_at", TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    Column("updated_at", TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
)

event_evidence = Table(
    "event_evidence", metadata, Column("event_id", String, nullable=False),
    Column("observation_id", String, nullable=False),
    Column("linked_at", TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    UniqueConstraint("event_id", "observation_id", name="uq_event_evidence_identity"),
)

event_reviews = Table(
    "event_reviews", metadata, Column("review_id", String, primary_key=True),
    Column("event_id", String, nullable=False), Column("decision", String, nullable=False),
    Column("notes", String), Column("reviewed_by", String, nullable=False),
    Column("reviewed_at", TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
)

canonical_player_projections = Table(
    "canonical_player_projections", metadata,
    Column("projection_id", String, primary_key=True), Column("event_id", String, nullable=False),
    Column("league_id", String, nullable=False), Column("player_id", String, nullable=False),
    Column("availability_before", String), Column("availability_after", String),
    Column("role_before", Float), Column("role_after", Float),
    Column("value_before", Float, nullable=False), Column("value_after", Float, nullable=False),
    Column("delta_json", String, nullable=False), Column("confidence", Float, nullable=False),
    Column("invalidation", String, nullable=False), Column("model_version", String, nullable=False),
    Column("computed_at", TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    UniqueConstraint(
        "event_id", "league_id", "player_id", "model_version",
        name="uq_canonical_player_projection_identity",
    ),
)

league_impacts = Table(
    "league_impacts", metadata, Column("impact_id", String, primary_key=True),
    Column("event_id", String, nullable=False), Column("league_id", String, nullable=False),
    Column("roster_id", Integer), Column("impact_type", String, nullable=False),
    Column("affected_asset_ids_json", String, nullable=False), Column("headline", String, nullable=False),
    Column("explanation", String, nullable=False), Column("before_json", String, nullable=False),
    Column("after_json", String, nullable=False), Column("deltas_json", String, nullable=False),
    Column("confidence", Float, nullable=False), Column("actionable", Boolean, nullable=False),
    Column("recommended_action", String), Column("cta_label", String), Column("cta_destination", String),
    Column("invalidation", String, nullable=False), Column("model_version", String, nullable=False),
    Column("computed_at", TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
)

daily_briefs = Table(
    "daily_briefs", metadata, Column("brief_id", String, primary_key=True),
    Column("brief_date", Date, nullable=False), Column("content_hash", String, nullable=False),
    Column("run_id", String, nullable=False),
    Column("status", String, nullable=False), Column("source_health_json", String, nullable=False),
    Column("created_at", TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    UniqueConstraint("brief_date", "content_hash"),
)

daily_brief_items = Table(
    "daily_brief_items", metadata, Column("item_id", String, primary_key=True),
    Column("brief_id", String, nullable=False), Column("event_id", String, nullable=False),
    Column("league_id", String), Column("roster_id", Integer), Column("lane", String, nullable=False),
    Column("priority_rank", Integer, nullable=False), Column("headline", String, nullable=False),
    Column("why_it_matters", String, nullable=False), Column("recommended_action", String),
    Column("confidence", Float, nullable=False), Column("source_summary", String, nullable=False),
    Column("invalidation", String, nullable=False), Column("impact_json", String, nullable=False),
    Column("cta_label", String), Column("cta_destination", String),
    Column("created_at", TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
)

brief_feedback = Table(
    "brief_feedback", metadata, Column("feedback_id", String, primary_key=True),
    Column("brief_id", String, nullable=False), Column("item_id", String, nullable=False),
    Column("verdict", String, nullable=False), Column("notes", String),
    Column("created_at", TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
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
    "team_schedule_weekly",
    "player_adp_baseline",
    "team_context_by_season",
    "freshness_domains",
    "intelligence_source_runs",
    "source_observations",
    "football_events",
    "event_evidence",
    "event_reviews",
    "canonical_player_projections",
    "league_impacts",
    "daily_briefs",
    "daily_brief_items",
    "brief_feedback",
]
