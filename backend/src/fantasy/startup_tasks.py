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
}

_SCHEMA_COMPAT_COLUMNS: dict[str, dict[str, str]] = {
    "rosters": {
        "owner_display_name": "VARCHAR",
    },
    "manager_profiles": {
        "trade_history": "VARCHAR",
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
