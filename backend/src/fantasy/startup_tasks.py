from __future__ import annotations

import logging
from typing import Any

import duckdb

from fantasy.config import Settings
from fantasy.ingestion.ingest_service import IngestService
from fantasy.ingestion.sleeper_client import SleeperClient
from fantasy.intelligence.intelligence_service import IntelligenceService
from fantasy.profiling.profiling_engine import ProfilingEngine
from fantasy.profiling.profiling_repo import ProfilingRepo
from fantasy.snapshots.snapshot_service import SnapshotService

logger = logging.getLogger(__name__)

_SCHEMA_COMPAT_TABLES: dict[str, str] = {
    "pick_values": """
        CREATE TABLE IF NOT EXISTS pick_values (
            id                      INTEGER PRIMARY KEY,
            league_id               VARCHAR NOT NULL,
            pick_owner_roster_id    INTEGER NOT NULL,
            pick_year               INTEGER NOT NULL,
            pick_round              INTEGER NOT NULL,
            computed_at             TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expected_draft_slot     FLOAT NOT NULL,
            base_value              FLOAT NOT NULL,
            timed_value             FLOAT NOT NULL,
            league_adjusted_value   FLOAT NOT NULL,
            demand_adjusted_value   FLOAT NOT NULL,
            timing_label            VARCHAR NOT NULL,
            timing_reasoning        VARCHAR NOT NULL,
            class_strength_signal   FLOAT NOT NULL DEFAULT 0.0,
            years_out               INTEGER NOT NULL DEFAULT 0,
            computation_json        VARCHAR,
            UNIQUE (league_id, pick_owner_roster_id, pick_year, pick_round)
        )
    """,
    "rookie_board_cache": """
        CREATE TABLE IF NOT EXISTS rookie_board_cache (
            id INTEGER PRIMARY KEY,
            league_id VARCHAR NOT NULL,
            computed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            class_strength_signal FLOAT NOT NULL,
            board_json VARCHAR NOT NULL
        )
    """,
    "league_draft_tendencies": """
        CREATE TABLE IF NOT EXISTS league_draft_tendencies (
            id INTEGER PRIMARY KEY,
            league_id VARCHAR NOT NULL,
            computed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            tendency_type VARCHAR NOT NULL,
            position VARCHAR,
            player_id VARCHAR,
            player_name VARCHAR,
            early_draft_slots FLOAT,
            adp_delta FLOAT,
            system_value_slot INTEGER
        )
    """,
    "draft_slots": """
        CREATE TABLE IF NOT EXISTS draft_slots (
            id              INTEGER PRIMARY KEY,
            league_id       VARCHAR NOT NULL,
            draft_id        VARCHAR NOT NULL,
            season          INTEGER NOT NULL,
            roster_id       INTEGER NOT NULL,
            confirmed_slot  INTEGER NOT NULL,
            status          VARCHAR NOT NULL,
            ingested_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (league_id, draft_id, roster_id)
        )
    """,
    "draft_pick_selections": """
        CREATE TABLE IF NOT EXISTS draft_pick_selections (
            id              INTEGER PRIMARY KEY,
            league_id       VARCHAR NOT NULL,
            draft_id        VARCHAR NOT NULL,
            roster_id       INTEGER NOT NULL,
            player_id       VARCHAR NOT NULL,
            pick_slot       INTEGER NOT NULL,
            round_number    INTEGER NOT NULL,
            season          INTEGER NOT NULL,
            draft_type      VARCHAR NOT NULL,
            position        VARCHAR,
            archetype_label VARCHAR,
            ingested_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (league_id, draft_id, roster_id, player_id)
        )
    """,
    "manager_rookie_pick_profiles": """
        CREATE TABLE IF NOT EXISTS manager_rookie_pick_profiles (
            id                       INTEGER PRIMARY KEY,
            league_id                VARCHAR NOT NULL,
            roster_id                INTEGER NOT NULL,
            computed_at              TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            pick_premium_score       FLOAT,
            pick_trade_evidence      INTEGER NOT NULL DEFAULT 0,
            draft_selection_count    INTEGER NOT NULL DEFAULT 0,
            positional_tendency_json VARCHAR NOT NULL DEFAULT '{}',
            dominant_archetype       VARCHAR,
            archetype_pattern_json   VARCHAR NOT NULL DEFAULT '{}',
            show_draft_picks_tab     BOOLEAN NOT NULL DEFAULT FALSE,
            UNIQUE (league_id, roster_id)
        )
    """,
    "calendar_overrides": """
        CREATE TABLE IF NOT EXISTS calendar_overrides (
            id         INTEGER PRIMARY KEY,
            league_id  VARCHAR NOT NULL UNIQUE,
            state      VARCHAR NOT NULL,
            set_by     VARCHAR NOT NULL DEFAULT 'user',
            set_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP
        )
    """,
    "freshness_domains": """
        CREATE TABLE IF NOT EXISTS freshness_domains (
            id           INTEGER PRIMARY KEY,
            league_id    VARCHAR NOT NULL,
            domain       VARCHAR NOT NULL,
            last_updated TIMESTAMP,
            notes        VARCHAR,
            UNIQUE (league_id, domain)
        )
    """,
    "league_draft_order_rules": """
        CREATE TABLE IF NOT EXISTS league_draft_order_rules (
            id                INTEGER PRIMARY KEY,
            league_id         VARCHAR NOT NULL UNIQUE,
            non_playoff_basis VARCHAR NOT NULL,
            playoff_ordering  VARCHAR NOT NULL,
            tiebreaker        VARCHAR NOT NULL,
            created_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "league_taxi_configs": """
        CREATE TABLE IF NOT EXISTS league_taxi_configs (
            id                  INTEGER PRIMARY KEY,
            league_id           VARCHAR NOT NULL UNIQUE,
            taxi_slots          INTEGER NOT NULL,
            taxi_years_eligible INTEGER NOT NULL,
            years_pro_cutoff    INTEGER NOT NULL,
            created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "league_format_acknowledgments": """
        CREATE TABLE IF NOT EXISTS league_format_acknowledgments (
            id                  INTEGER PRIMARY KEY,
            league_id           VARCHAR NOT NULL UNIQUE,
            acknowledged_rules  VARCHAR NOT NULL,
            acknowledged_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "lineup_scores": """
        CREATE TABLE IF NOT EXISTS lineup_scores (
            id                      INTEGER PRIMARY KEY,
            league_id               VARCHAR NOT NULL,
            roster_id               INTEGER NOT NULL,
            computed_at             TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            total_lineup_score      FLOAT NOT NULL,
            title_window_label      VARCHAR NOT NULL,
            title_window_composite  FLOAT NOT NULL,
            ceiling_score           FLOAT NOT NULL,
            stability_score         FLOAT NOT NULL,
            depth_score             FLOAT NOT NULL,
            slot_scores_json        VARCHAR NOT NULL,
            UNIQUE (league_id, roster_id)
        )
    """,
    "hygiene_suggestions": """
        CREATE TABLE IF NOT EXISTS hygiene_suggestions (
            id                      INTEGER PRIMARY KEY,
            league_id               VARCHAR NOT NULL,
            roster_id               INTEGER NOT NULL,
            computed_at             TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            suggestions_json        VARCHAR NOT NULL,
            UNIQUE (league_id, roster_id)
        )
    """,
    "retrospective_runs": """
        CREATE TABLE IF NOT EXISTS retrospective_runs (
            id INTEGER PRIMARY KEY,
            run_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            run_type VARCHAR NOT NULL,
            season VARCHAR NOT NULL,
            grades_json VARCHAR NOT NULL,
            notes VARCHAR
        )
    """,
    "historical_prospect_features": """
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
            college_games INTEGER,
            college_targets DOUBLE,
            college_receptions DOUBLE,
            college_receiving_yards DOUBLE,
            college_receiving_tds DOUBLE,
            college_routes_run DOUBLE,
            college_carries DOUBLE,
            college_rushing_yards DOUBLE,
            college_rushing_tds DOUBLE,
            college_pass_attempts DOUBLE,
            college_completions DOUBLE,
            college_passing_yards DOUBLE,
            college_passing_tds DOUBLE,
            college_interceptions DOUBLE,
            college_rec_ypg DOUBLE,
            college_rush_ypg DOUBLE,
            college_yprr DOUBLE,
            college_ypt DOUBLE,
            college_ypc DOUBLE,
            college_ypa DOUBLE,
            college_pass_td_rate DOUBLE,
            college_qb_rush_yards DOUBLE,
            college_qb_rush_tds DOUBLE,
            college_qb_rush_ypg DOUBLE,
            college_scramble_rate DOUBLE,
            college_mkt_share_proxy DOUBLE,
            college_td_rate DOUBLE,
            college_completion_pct_proxy DOUBLE,
            adp DOUBLE,
            archetype_label VARCHAR,
            outcome_bucket VARCHAR,
            PRIMARY KEY (player_id, draft_year)
        )
    """,
    "prospect_model_outputs": """
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
    """,
    "prospect_sub_flags": """
        CREATE TABLE IF NOT EXISTS prospect_sub_flags (
            id INTEGER PRIMARY KEY,
            league_id VARCHAR NOT NULL,
            player_id VARCHAR NOT NULL,
            signal_name VARCHAR NOT NULL,
            direction VARCHAR NOT NULL,
            magnitude_str VARCHAR NOT NULL
        )
    """,
    "waiver_recommendations": """
        CREATE TABLE IF NOT EXISTS waiver_recommendations (
            id                   INTEGER PRIMARY KEY,
            league_id            VARCHAR NOT NULL,
            roster_id            INTEGER NOT NULL,
            computed_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            recommendations_json VARCHAR NOT NULL,
            UNIQUE (league_id, roster_id)
        )
    """,
    "startup_contexts": """
        CREATE TABLE IF NOT EXISTS startup_contexts (
            id             INTEGER PRIMARY KEY,
            league_id      VARCHAR NOT NULL UNIQUE,
            computed_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            draft_status   VARCHAR NOT NULL,
            build_template VARCHAR NOT NULL,
            context_json   VARCHAR NOT NULL
        )
    """,
    "orphan_intakes": """
        CREATE TABLE IF NOT EXISTS orphan_intakes (
            id                     INTEGER PRIMARY KEY,
            league_id              VARCHAR NOT NULL,
            roster_id              INTEGER NOT NULL,
            computed_at            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            age_curve_score        FLOAT NOT NULL,
            pick_capital_score     FLOAT NOT NULL,
            dead_spots_score       FLOAT NOT NULL,
            lineup_viability_score FLOAT NOT NULL,
            liquidation_score      FLOAT NOT NULL,
            composite_score        FLOAT NOT NULL,
            intake_json            VARCHAR NOT NULL,
            UNIQUE (league_id, roster_id)
        )
    """,
    "action_plans": """
        CREATE TABLE IF NOT EXISTS action_plans (
            id          INTEGER PRIMARY KEY,
            league_id   VARCHAR NOT NULL,
            roster_id   INTEGER NOT NULL,
            computed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            plan_type   VARCHAR NOT NULL,
            items_json  VARCHAR NOT NULL,
            summary     VARCHAR NOT NULL,
            UNIQUE (league_id, roster_id)
        )
    """,
}

_SCHEMA_COMPAT_COLUMNS: dict[str, dict[str, str]] = {
    "rosters": {
        "owner_display_name": "VARCHAR",
        "waiver_position": "INTEGER",
        "waiver_budget_used": "INTEGER",
    },
    "manager_profiles": {
        "trade_history": "VARCHAR",
    },
    "transactions": {
        "waiver_bid": "INTEGER",
    },
}


def parse_dev_refresh_leagues(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def resolve_dev_refresh_league_ids(
    conn: duckdb.DuckDBPyConnection, configured_league_ids: list[str]
) -> list[str]:
    if configured_league_ids:
        return configured_league_ids
    rows = conn.execute(
        """
        SELECT league_id
        FROM leagues
        ORDER BY league_id
        """
    ).fetchall()
    return [str(row[0]) for row in rows]


def ensure_runtime_schema(conn: duckdb.DuckDBPyConnection) -> None:
    existing_tables = {
        str(row[0])
        for row in conn.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'main'
            """
        ).fetchall()
    }
    for table_name, create_sql in _SCHEMA_COMPAT_TABLES.items():
        if table_name in existing_tables:
            continue
        conn.execute(create_sql)
        existing_tables.add(table_name)
        logger.info("Created runtime schema table %s.", table_name)
    for table_name, columns in _SCHEMA_COMPAT_COLUMNS.items():
        if table_name not in existing_tables:
            continue
        existing_columns = {
            str(row[0])
            for row in conn.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = ?
                """,
                [table_name],
            ).fetchall()
        }
        for column_name, column_type in columns.items():
            if column_name in existing_columns:
                continue
            conn.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            )
            if table_name == "manager_profiles" and column_name == "trade_history":
                conn.execute(
                    """
                    UPDATE manager_profiles
                    SET trade_history = '[]'
                    WHERE trade_history IS NULL
                    """
                )
            logger.info("Added runtime schema column %s.%s.", table_name, column_name)


def refresh_league_artifacts(
    conn: duckdb.DuckDBPyConnection,
    league_id: str,
    *,
    include_snapshot: bool = True,
) -> dict[str, Any]:
    result = IntelligenceService(conn).compute_league(league_id)
    profiles = ProfilingEngine(conn).compute_all_profiles(league_id)
    profiling_repo = ProfilingRepo(conn)
    for profile in profiles:
        profiling_repo.upsert_profile(profile)
        profiling_repo.replace_pitch_angles(
            profile.league_id, profile.roster_id, profile.pitch_angles
        )
    snapshot_ids = (
        SnapshotService(conn).take_snapshot([league_id], triggered_by="manual")
        if include_snapshot
        else []
    )
    return {
        "league_id": league_id,
        "roster_count": len(result["scorecards"]),
        "player_value_count": sum(len(values) for values in result["values"].values()),
        "manager_profile_count": len(profiles),
        "snapshot_count": len(snapshot_ids),
    }


async def maybe_run_dev_refresh(
    conn: duckdb.DuckDBPyConnection,
    settings: Settings,
) -> None:
    ensure_runtime_schema(conn)
    if not settings.DEV_AUTO_REFRESH:
        return

    league_ids = resolve_dev_refresh_league_ids(
        conn, parse_dev_refresh_leagues(settings.DEV_AUTO_REFRESH_LEAGUES)
    )
    if not league_ids:
        logger.info("Dev auto-refresh enabled, but no leagues were resolved.")
        return

    logger.info(
        "Dev auto-refresh enabled for %s league(s): %s",
        len(league_ids),
        ", ".join(league_ids),
    )

    if settings.DEV_AUTO_REFRESH_INGEST_MODE != "skip":
        async with SleeperClient() as client:
            ingest_service = IngestService(conn, client)
            for league_id in league_ids:
                try:
                    run_id = await ingest_service.run(
                        league_id, settings.DEV_AUTO_REFRESH_INGEST_MODE
                    )
                    logger.info(
                        "Dev auto-refresh ingest finished for %s with run_id=%s.",
                        league_id,
                        run_id,
                    )
                except Exception:
                    logger.exception(
                        "Dev auto-refresh ingest failed for %s.", league_id
                    )

    for league_id in league_ids:
        try:
            summary = refresh_league_artifacts(
                conn,
                league_id,
                include_snapshot=settings.DEV_AUTO_REFRESH_SNAPSHOTS,
            )
            logger.info(
                "Dev auto-refresh rebuilt %s: %s rosters, %s player values, %s profiles, %s snapshots.",
                league_id,
                summary["roster_count"],
                summary["player_value_count"],
                summary["manager_profile_count"],
                summary["snapshot_count"],
            )
        except Exception:
            logger.exception(
                "Dev auto-refresh compute phase failed for %s.", league_id
            )
