from fantasy.startup_tasks import (
    ensure_runtime_schema,
    parse_dev_refresh_leagues,
    refresh_league_artifacts,
    resolve_dev_refresh_league_ids,
)


def test_parse_dev_refresh_leagues_trims_empty_values():
    assert parse_dev_refresh_leagues("") == []
    assert parse_dev_refresh_leagues(" league_a, ,league_b ,, league_c ") == [
        "league_a",
        "league_b",
        "league_c",
    ]


def test_resolve_dev_refresh_league_ids_uses_configured_values_first(phase2_seed_data):
    assert resolve_dev_refresh_league_ids(phase2_seed_data, ["league_b", "league_a"]) == [
        "league_b",
        "league_a",
    ]
    assert resolve_dev_refresh_league_ids(phase2_seed_data, []) == ["league_x"]


def test_ensure_runtime_schema_adds_missing_columns(db):
    db.execute("DROP TABLE rosters")
    db.execute("DROP TABLE manager_profiles")
    db.execute(
        """
        CREATE TABLE rosters (
            id INTEGER PRIMARY KEY,
            league_id VARCHAR NOT NULL,
            roster_id INTEGER NOT NULL,
            owner_id VARCHAR,
            starters VARCHAR NOT NULL,
            players VARCHAR NOT NULL,
            reserve VARCHAR,
            taxi VARCHAR,
            ingested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    db.execute(
        """
        CREATE TABLE manager_profiles (
            id INTEGER PRIMARY KEY,
            league_id VARCHAR NOT NULL,
            roster_id INTEGER NOT NULL,
            computed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            evidence_count INTEGER NOT NULL,
            low_confidence BOOLEAN NOT NULL,
            exploitability_score DOUBLE NOT NULL,
            exploitation_primary VARCHAR,
            exploitation_secondary VARCHAR,
            exploitation_evidence VARCHAR NOT NULL,
            roster_summary VARCHAR,
            aggregate_trade_stats VARCHAR NOT NULL
        )
        """
    )
    db.execute(
        """
        INSERT INTO manager_profiles (
            id, league_id, roster_id, evidence_count, low_confidence,
            exploitability_score, exploitation_primary, exploitation_secondary,
            exploitation_evidence, roster_summary, aggregate_trade_stats
        )
        VALUES (1, 'league_x', 1, 0, TRUE, 0.0, NULL, NULL, '{}', '{}', '{}')
        """
    )

    ensure_runtime_schema(db)

    roster_columns = {
        row[0]
        for row in db.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'rosters'
            """
        ).fetchall()
    }
    profile_columns = {
        row[0]
        for row in db.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'manager_profiles'
            """
        ).fetchall()
    }
    assert "owner_display_name" in roster_columns
    assert "trade_history" in profile_columns
    trade_history = db.execute(
        """
        SELECT trade_history
        FROM manager_profiles
        WHERE league_id = 'league_x' AND roster_id = 1
        """
    ).fetchone()
    assert trade_history == ("[]",)


def test_ensure_runtime_schema_creates_missing_phase_tables(db):
    for table_name in [
        "draft_slots",
        "pick_values",
        "rookie_board_cache",
        "league_draft_tendencies",
        "league_draft_order_rules",
    ]:
        db.execute(f"DROP TABLE {table_name}")

    ensure_runtime_schema(db)

    tables = {
        row[0]
        for row in db.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'main'
            """
        ).fetchall()
    }
    assert "draft_slots" in tables
    assert "pick_values" in tables
    assert "rookie_board_cache" in tables
    assert "league_draft_tendencies" in tables
    assert "league_draft_order_rules" in tables


def test_league_draft_order_rules_table_created_by_startup(db):
    db.execute("DROP TABLE IF EXISTS league_draft_order_rules")

    ensure_runtime_schema(db)

    db.execute(
        """
        INSERT INTO league_draft_order_rules (
            id,
            league_id,
            non_playoff_basis,
            playoff_ordering,
            tiebreaker
        )
        VALUES (1, 'test_league', 'inverse_standings', 'by_finish', 'points_against')
        """
    )
    row = db.execute(
        """
        SELECT league_id
        FROM league_draft_order_rules
        WHERE id = 1
        """
    ).fetchone()
    assert row == ("test_league",)


def test_refresh_league_artifacts_rebuilds_cached_outputs(phase2_seed_data):
    summary = refresh_league_artifacts(phase2_seed_data, "league_x")

    assert summary["league_id"] == "league_x"
    assert summary["roster_count"] == 2
    assert summary["player_value_count"] > 0
    assert summary["manager_profile_count"] == 2
    assert summary["snapshot_count"] == 1
    assert (
        phase2_seed_data.execute(
            "SELECT COUNT(*) FROM manager_profiles WHERE league_id = 'league_x'"
        ).fetchone()[0]
        == 2
    )
