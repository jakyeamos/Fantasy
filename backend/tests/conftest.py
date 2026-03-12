import duckdb
import pytest

SCHEMA_SQL = [
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
    """
    CREATE TABLE IF NOT EXISTS player_stats_weekly (
        player_id VARCHAR NOT NULL,
        player_name VARCHAR,
        position VARCHAR,
        season INTEGER NOT NULL,
        week INTEGER NOT NULL,
        receptions DOUBLE,
        targets DOUBLE,
        receiving_yards DOUBLE,
        receiving_tds DOUBLE,
        rushing_yards DOUBLE,
        rushing_tds DOUBLE,
        carries DOUBLE,
        passing_yards DOUBLE,
        passing_tds DOUBLE,
        interceptions DOUBLE,
        passing_2pt_conversions DOUBLE,
        receiving_2pt_conversions DOUBLE,
        rushing_2pt_conversions DOUBLE,
        fantasy_points DOUBLE,
        UNIQUE (player_id, season, week)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS player_adp_baseline (
        player_id VARCHAR,
        player_name VARCHAR,
        position VARCHAR,
        adp DOUBLE,
        adp_source VARCHAR,
        loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
]


@pytest.fixture
def db():
    conn = duckdb.connect(":memory:")
    for statement in SCHEMA_SQL:
        conn.execute(statement)
    yield conn
    conn.close()


@pytest.fixture
def mock_league_response():
    return {
        "league_id": "test_league_001",
        "name": "Test Dynasty League",
        "season": "2025",
        "scoring_settings": {
            "rec": 1.0,
            "rec_yd": 0.1,
            "rush_yd": 0.1,
            "pass_yd": 0.04,
            "pass_td": 4.0,
            "rec_td": 6.0,
            "rush_td": 6.0,
            "bonus_rec_te": 0.5,
        },
        "roster_positions": [
            "QB",
            "RB",
            "RB",
            "WR",
            "WR",
            "TE",
            "SUPER_FLEX",
            "BN",
            "BN",
            "BN",
            "BN",
            "BN",
            "BN",
        ],
        "settings": {"num_teams": 12, "taxi_slots": 4, "reserve_slots": 2},
    }


@pytest.fixture
def mock_roster_response():
    return {
        "roster_id": 1,
        "owner_id": "user_abc",
        "league_id": "test_league_001",
        "starters": ["4017", "4663"],
        "players": ["4017", "4663", "2374", "6945"],
        "reserve": ["5122"],
        "taxi": ["8888"],
        "settings": {
            "wins": 9,
            "losses": 4,
            "ties": 0,
            "fpts": 1534,
            "fpts_decimal": 5,
            "fpts_against": 1402.5,
        },
    }


@pytest.fixture
def mock_traded_pick_response():
    return [
        {
            "season": "2025",
            "round": 1,
            "roster_id": 3,
            "owner_id": 7,
            "previous_owner_id": 3,
            "league_id": "test_league_001",
        },
        {
            "season": "2026",
            "round": 2,
            "roster_id": 5,
            "owner_id": 5,
            "previous_owner_id": None,
            "league_id": "test_league_001",
        },
    ]


@pytest.fixture
def mock_transaction_response():
    return [
        {
            "transaction_id": "txn_001",
            "type": "trade",
            "status": "complete",
            "created": 1700000000000,
            "roster_ids": [1, 3],
            "adds": {"4017": 3, "2374": 1},
            "drops": {"4017": 1, "2374": 3},
            "draft_picks": [{"season": "2025", "round": 1, "roster_id": 1, "owner_id": 3}],
            "leg": 1,
        },
        {
            "transaction_id": "txn_002",
            "type": "free_agent",
            "status": "complete",
            "created": 1700100000000,
            "roster_ids": [2],
            "adds": {"6945": 2},
            "drops": None,
            "draft_picks": [],
            "leg": 5,
        },
    ]
