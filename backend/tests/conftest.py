import json
from datetime import datetime, timedelta

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
        owner_display_name VARCHAR,
        waiver_position INTEGER,
        waiver_budget_used INTEGER,
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
    CREATE TABLE IF NOT EXISTS draft_slots (
        id INTEGER PRIMARY KEY,
        league_id VARCHAR NOT NULL,
        draft_id VARCHAR NOT NULL,
        season INTEGER NOT NULL,
        roster_id INTEGER NOT NULL,
        confirmed_slot INTEGER NOT NULL,
        status VARCHAR NOT NULL,
        ingested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (league_id, draft_id, roster_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS draft_pick_selections (
        id INTEGER PRIMARY KEY,
        league_id VARCHAR NOT NULL,
        draft_id VARCHAR NOT NULL,
        roster_id INTEGER NOT NULL,
        player_id VARCHAR NOT NULL,
        pick_slot INTEGER NOT NULL,
        round_number INTEGER NOT NULL,
        season INTEGER NOT NULL,
        draft_type VARCHAR NOT NULL,
        position VARCHAR,
        archetype_label VARCHAR,
        ingested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (league_id, draft_id, roster_id, player_id)
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
        waiver_bid INTEGER,
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
        mfl_id VARCHAR,
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
    """
    CREATE TABLE IF NOT EXISTS team_scorecards (
        id INTEGER PRIMARY KEY,
        league_id VARCHAR NOT NULL,
        roster_id INTEGER NOT NULL,
        computed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        win_now DOUBLE NOT NULL,
        future_value DOUBLE NOT NULL,
        depth DOUBLE NOT NULL,
        pick_capital DOUBLE NOT NULL,
        flexibility DOUBLE NOT NULL,
        fragility DOUBLE NOT NULL,
        age_risk DOUBLE NOT NULL,
        liquidity DOUBLE NOT NULL,
        positional_insulation DOUBLE NOT NULL,
        composite DOUBLE NOT NULL,
        computation_json VARCHAR,
        UNIQUE (league_id, roster_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS team_directions (
        id INTEGER PRIMARY KEY,
        league_id VARCHAR NOT NULL,
        roster_id INTEGER NOT NULL,
        computed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        primary_label VARCHAR NOT NULL,
        confidence DOUBLE NOT NULL,
        reasoning VARCHAR NOT NULL,
        alternates_json VARCHAR NOT NULL,
        delta_json VARCHAR NOT NULL,
        approved_moves VARCHAR NOT NULL,
        discouraged_moves VARCHAR NOT NULL,
        UNIQUE (league_id, roster_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS player_values (
        id INTEGER PRIMARY KEY,
        league_id VARCHAR NOT NULL,
        roster_id INTEGER NOT NULL,
        player_id VARCHAR NOT NULL,
        computed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        comp_current_production DOUBLE,
        comp_short_term DOUBLE,
        comp_role_stability DOUBLE,
        comp_age_curve DOUBLE,
        comp_insulation DOUBLE,
        comp_market_liquidity DOUBLE,
        comp_positional_scarcity DOUBLE,
        comp_fragility DOUBLE,
        comp_ceiling DOUBLE,
        comp_floor DOUBLE,
        comp_rerollability DOUBLE,
        comp_contract DOUBLE,
        lens_production DOUBLE,
        lens_market DOUBLE,
        lens_insulation DOUBLE,
        lens_team_fit DOUBLE,
        lens_direction DOUBLE,
        UNIQUE (league_id, roster_id, player_id)
    )
    """,
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
    """,
    """
    CREATE TABLE IF NOT EXISTS manager_profiles (
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
        aggregate_trade_stats VARCHAR NOT NULL,
        trade_history VARCHAR NOT NULL DEFAULT '[]',
        UNIQUE (league_id, roster_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS manager_pitch_angles (
        id INTEGER PRIMARY KEY,
        league_id VARCHAR NOT NULL,
        roster_id INTEGER NOT NULL,
        rank INTEGER NOT NULL,
        deal_archetype VARCHAR NOT NULL,
        send_description VARCHAR NOT NULL,
        avoid_description VARCHAR NOT NULL,
        reasoning VARCHAR NOT NULL,
        computed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (league_id, roster_id, rank)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS manager_rookie_pick_profiles (
        id INTEGER PRIMARY KEY,
        league_id VARCHAR NOT NULL,
        roster_id INTEGER NOT NULL,
        computed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        pick_premium_score DOUBLE,
        pick_trade_evidence INTEGER NOT NULL DEFAULT 0,
        draft_selection_count INTEGER NOT NULL DEFAULT 0,
        positional_tendency_json VARCHAR NOT NULL DEFAULT '{}',
        dominant_archetype VARCHAR,
        archetype_pattern_json VARCHAR NOT NULL DEFAULT '{}',
        show_draft_picks_tab BOOLEAN NOT NULL DEFAULT FALSE,
        UNIQUE (league_id, roster_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS calendar_overrides (
        id INTEGER PRIMARY KEY,
        league_id VARCHAR NOT NULL UNIQUE,
        state VARCHAR NOT NULL,
        set_by VARCHAR NOT NULL DEFAULT 'user',
        set_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS freshness_domains (
        id INTEGER PRIMARY KEY,
        league_id VARCHAR NOT NULL,
        domain VARCHAR NOT NULL,
        last_updated TIMESTAMP,
        notes VARCHAR,
        UNIQUE (league_id, domain)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pick_values (
        id INTEGER PRIMARY KEY,
        league_id VARCHAR NOT NULL,
        pick_owner_roster_id INTEGER NOT NULL,
        pick_year INTEGER NOT NULL,
        pick_round INTEGER NOT NULL,
        computed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        expected_draft_slot DOUBLE NOT NULL,
        base_value DOUBLE NOT NULL,
        timed_value DOUBLE NOT NULL,
        league_adjusted_value DOUBLE NOT NULL,
        demand_adjusted_value DOUBLE NOT NULL,
        timing_label VARCHAR NOT NULL,
        timing_reasoning VARCHAR NOT NULL,
        class_strength_signal DOUBLE NOT NULL DEFAULT 0.0,
        years_out INTEGER NOT NULL DEFAULT 0,
        computation_json VARCHAR,
        UNIQUE (league_id, pick_owner_roster_id, pick_year, pick_round)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS rookie_board_cache (
        id INTEGER PRIMARY KEY,
        league_id VARCHAR NOT NULL,
        computed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        class_strength_signal DOUBLE NOT NULL,
        board_json VARCHAR NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS league_draft_tendencies (
        id INTEGER PRIMARY KEY,
        league_id VARCHAR NOT NULL,
        computed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        tendency_type VARCHAR NOT NULL,
        position VARCHAR,
        player_id VARCHAR,
        player_name VARCHAR,
        early_draft_slots DOUBLE,
        adp_delta DOUBLE,
        system_value_slot INTEGER
    )
    """,
    """
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
    """
    CREATE TABLE IF NOT EXISTS league_taxi_configs (
        id                     INTEGER PRIMARY KEY,
        league_id              VARCHAR NOT NULL UNIQUE,
        taxi_slots             INTEGER NOT NULL,
        taxi_years_eligible    INTEGER NOT NULL,
        years_pro_cutoff       INTEGER NOT NULL,
        manual_exceptions_json VARCHAR NOT NULL DEFAULT '[]',
        created_at             TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at             TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS league_format_acknowledgments (
        id INTEGER PRIMARY KEY,
        league_id VARCHAR NOT NULL UNIQUE,
        acknowledged_rules VARCHAR NOT NULL,
        acknowledged_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
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
        recommendation_cards_json VARCHAR NOT NULL DEFAULT '[]',
        UNIQUE (league_id, roster_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS hygiene_suggestions (
        id                      INTEGER PRIMARY KEY,
        league_id               VARCHAR NOT NULL,
        roster_id               INTEGER NOT NULL,
        computed_at             TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        suggestions_json        VARCHAR NOT NULL,
        recommendation_cards_json VARCHAR NOT NULL DEFAULT '[]',
        UNIQUE (league_id, roster_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS retrospective_runs (
        id INTEGER PRIMARY KEY,
        run_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        run_type VARCHAR NOT NULL,
        season VARCHAR NOT NULL,
        grades_json VARCHAR NOT NULL,
        notes VARCHAR
    )
    """,
    """
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
    """
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
    """
    CREATE TABLE IF NOT EXISTS prospect_sub_flags (
        id INTEGER PRIMARY KEY,
        league_id VARCHAR NOT NULL,
        player_id VARCHAR NOT NULL,
        signal_name VARCHAR NOT NULL,
        direction VARCHAR NOT NULL,
        magnitude_str VARCHAR NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS waiver_recommendations (
        id INTEGER PRIMARY KEY,
        league_id VARCHAR NOT NULL,
        roster_id INTEGER NOT NULL,
        computed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        recommendations_json VARCHAR NOT NULL,
        UNIQUE (league_id, roster_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS startup_contexts (
        id INTEGER PRIMARY KEY,
        league_id VARCHAR NOT NULL UNIQUE,
        computed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        draft_status VARCHAR NOT NULL,
        build_template VARCHAR NOT NULL,
        context_json VARCHAR NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS orphan_intakes (
        id INTEGER PRIMARY KEY,
        league_id VARCHAR NOT NULL,
        roster_id INTEGER NOT NULL,
        computed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        age_curve_score FLOAT NOT NULL,
        pick_capital_score FLOAT NOT NULL,
        dead_spots_score FLOAT NOT NULL,
        lineup_viability_score FLOAT NOT NULL,
        liquidation_score FLOAT NOT NULL,
        composite_score FLOAT NOT NULL,
        intake_json VARCHAR NOT NULL,
        UNIQUE (league_id, roster_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS action_plans (
        id INTEGER PRIMARY KEY,
        league_id VARCHAR NOT NULL,
        roster_id INTEGER NOT NULL,
        computed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        plan_type VARCHAR NOT NULL,
        items_json VARCHAR NOT NULL,
        summary VARCHAR NOT NULL,
        UNIQUE (league_id, roster_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS player_context_flags (
        id INTEGER PRIMARY KEY,
        player_id VARCHAR NOT NULL,
        flag_type VARCHAR NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP,
        source VARCHAR NOT NULL DEFAULT 'sleeper_ingest',
        metadata_json VARCHAR,
        UNIQUE (player_id, flag_type)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS market_values (
        id INTEGER PRIMARY KEY,
        player_id VARCHAR NOT NULL,
        fetched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        fantasycalc_value DOUBLE,
        fantasycalc_rank INTEGER,
        fantasycalc_trend30 DOUBLE,
        adp_baseline DOUBLE,
        UNIQUE (player_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS player_trends (
        id                       INTEGER PRIMARY KEY,
        player_id                VARCHAR NOT NULL,
        season                   INTEGER NOT NULL,
        trend_label              VARCHAR,
        confidence               VARCHAR,
        delta_magnitude          FLOAT,
        adp_delta                FLOAT,
        comp_current_production  FLOAT,
        comp_short_term          FLOAT,
        comp_role_stability      FLOAT,
        comp_age_curve           FLOAT,
        comp_insulation          FLOAT,
        comp_market_liquidity    FLOAT,
        comp_positional_scarcity FLOAT,
        comp_fragility           FLOAT,
        comp_ceiling             FLOAT,
        comp_floor               FLOAT,
        comp_rerollability       FLOAT,
        comp_contract            FLOAT,
        startup_adp              FLOAT,
        backfilled               BOOLEAN NOT NULL DEFAULT FALSE,
        computed_at              TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (player_id, season)
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
            "waiver_position": 3,
            "waiver_budget_used": 27,
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


@pytest.fixture
def phase2_seed_data(db):
    db.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions,
            settings_blob, superflex, tep, ppr
        )
        VALUES
            ('league_x', 'League X', '2025', '{"rec":1.0}', '["QB","RB","WR","TE","SUPER_FLEX","BN","BN"]', '{"num_teams":2}', TRUE, FALSE, 1.0)
        """
    )
    db.execute(
        """
        INSERT INTO rosters (id, league_id, roster_id, owner_id, starters, players, reserve, taxi)
        VALUES
            (1, 'league_x', 1, 'user_a', '["qb1","rb1","wr1","te1"]', '["qb1","rb1","wr1","te1","rbb1","wrb1"]', '[]', '[]'),
            (2, 'league_x', 2, 'user_b', '["qb2","rb2","wr2","te2"]', '["qb2","rb2","wr2","te2","rbb2","wrb2"]', '[]', '[]')
        """
    )
    db.execute(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES
            ('qb1','QB One','QB','A',24,'{}'),
            ('rb1','RB One','RB','A',24,'{}'),
            ('wr1','WR One','WR','A',23,'{}'),
            ('te1','TE One','TE','A',25,'{}'),
            ('rbb1','RB Bench One','RB','A',22,'{}'),
            ('wrb1','WR Bench One','WR','A',22,'{}'),
            ('qb2','QB Two','QB','B',33,'{}'),
            ('rb2','RB Two','RB','B',29,'{}'),
            ('wr2','WR Two','WR','B',31,'{}'),
            ('te2','TE Two','TE','B',30,'{}'),
            ('rbb2','RB Bench Two','RB','B',28,'{}'),
            ('wrb2','WR Bench Two','WR','B',28,'{}'),
            ('rookie1','Rookie One','WR','C',21,'{}'),
            ('vet1','Vet One','RB','C',30,'{}')
        """
    )
    stats_rows = [
        ("qb1", "QB One", "QB", 2024, 1, 0, 0, 0, 0, 20, 1, 3, 250, 2, 0, 0, 0, 0, 22),
        ("rb1", "RB One", "RB", 2024, 1, 3, 4, 20, 0, 90, 1, 18, 0, 0, 0, 0, 0, 0, 20),
        ("wr1", "WR One", "WR", 2024, 1, 7, 8, 90, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 22),
        ("te1", "TE One", "TE", 2024, 1, 5, 6, 55, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 16),
        ("rbb1", "RB Bench One", "RB", 2024, 1, 2, 2, 10, 0, 40, 0, 8, 0, 0, 0, 0, 0, 0, 7),
        ("wrb1", "WR Bench One", "WR", 2024, 1, 3, 4, 40, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 7),
        ("qb2", "QB Two", "QB", 2024, 1, 0, 0, 0, 0, 10, 0, 2, 200, 1, 1, 0, 0, 0, 14),
        ("rb2", "RB Two", "RB", 2024, 1, 1, 2, 5, 0, 50, 0, 12, 0, 0, 0, 0, 0, 0, 8),
        ("wr2", "WR Two", "WR", 2024, 1, 4, 6, 35, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 7),
        ("te2", "TE Two", "TE", 2024, 1, 3, 4, 25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5),
        ("rbb2", "RB Bench Two", "RB", 2024, 1, 1, 1, 5, 0, 15, 0, 4, 0, 0, 0, 0, 0, 0, 3),
        ("wrb2", "WR Bench Two", "WR", 2024, 1, 1, 2, 10, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3),
        ("rookie1", "Rookie One", "WR", 2024, 1, 2, 2, 18, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5),
        ("vet1", "Vet One", "RB", 2024, 1, 1, 1, 2, 0, 30, 0, 9, 0, 0, 0, 0, 0, 0, 5),
    ]
    db.executemany(
        """
        INSERT INTO player_stats_weekly (
            player_id, player_name, position, season, week, receptions, targets,
            receiving_yards, receiving_tds, rushing_yards, rushing_tds, carries,
            passing_yards, passing_tds, interceptions, passing_2pt_conversions,
            receiving_2pt_conversions, rushing_2pt_conversions, fantasy_points
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        stats_rows,
    )
    db.execute(
        """
        INSERT INTO player_adp_baseline (player_id, player_name, position, adp, adp_source)
        VALUES
            ('qb1','QB One','QB',30,'test'),
            ('rb1','RB One','RB',20,'test'),
            ('wr1','WR One','WR',10,'test'),
            ('te1','TE One','TE',45,'test'),
            ('rbb1','RB Bench One','RB',90,'test'),
            ('wrb1','WR Bench One','WR',110,'test'),
            ('qb2','QB Two','QB',85,'test'),
            ('rb2','RB Two','RB',95,'test'),
            ('wr2','WR Two','WR',120,'test'),
            ('te2','TE Two','TE',150,'test'),
            ('rbb2','RB Bench Two','RB',170,'test'),
            ('wrb2','WR Bench Two','WR',180,'test'),
            ('rookie1','Rookie One','WR',50,'test'),
            ('vet1','Vet One','RB',130,'test')
        """
    )
    db.execute(
        """
        INSERT INTO traded_picks (id, league_id, season, round, roster_id, owner_id, previous_owner_id)
        VALUES
            (1, 'league_x', '2025', 1, 2, '1', '2'),
            (2, 'league_x', '2026', 2, 2, '1', '2')
        """
    )
    return db


@pytest.fixture
def phase3_seed_data(phase2_seed_data):
    phase2_seed_data.execute(
        """
        INSERT INTO transactions (
            transaction_id, league_id, type, status, created_at,
            roster_ids, adds, drops, draft_picks, week
        )
        VALUES
            (
                'trade_1',
                'league_x',
                'trade',
                'complete',
                CURRENT_TIMESTAMP,
                '[1,2]',
                '{"wr2":1,"vet1":2}',
                '{"vet1":1,"wr2":2}',
                '[{"season":"2026","round":1,"roster_id":2,"owner_id":1,"previous_owner_id":2}]',
                5
            ),
            (
                'trade_2',
                'league_x',
                'trade',
                'complete',
                CURRENT_TIMESTAMP,
                '[1,2]',
                '{"rookie1":2,"wrb1":1}',
                '{"wrb1":2,"rookie1":1}',
                '[]',
                6
            )
        """
    )
    return phase2_seed_data


@pytest.fixture
def profiling_seed_data(phase2_seed_data):
    phase2_seed_data.execute("DELETE FROM transactions WHERE league_id = 'league_x'")
    phase2_seed_data.execute(
        """
        INSERT INTO team_directions (
            id, league_id, roster_id, primary_label, confidence, reasoning,
            alternates_json, delta_json, approved_moves, discouraged_moves
        )
        VALUES
            (
                1, 'league_x', 1, 'hard_rebuild', 0.92, 'seeded',
                '[]', '{}', '[]', '[]'
            ),
            (
                2, 'league_x', 2, 'true_contender', 0.88, 'seeded',
                '[]', '{}', '[]', '[]'
            )
        ON CONFLICT (league_id, roster_id) DO UPDATE SET
            primary_label = EXCLUDED.primary_label,
            confidence = EXCLUDED.confidence,
            reasoning = EXCLUDED.reasoning,
            alternates_json = EXCLUDED.alternates_json,
            delta_json = EXCLUDED.delta_json,
            approved_moves = EXCLUDED.approved_moves,
            discouraged_moves = EXCLUDED.discouraged_moves
        """
    )

    base_time = datetime(2025, 1, 1, 12, 0, 0)
    trade_rows = [
        ("prof_trade_1", "qb2", "wr1", 1, 4),
        ("prof_trade_2", "qb2", "rb1", 2, 5),
        ("prof_trade_3", "qb2", "rookie1", 1, 6),
        ("prof_trade_4", "qb2", "qb1", 0, 7),
        ("prof_trade_5", "qb2", "te1", 0, 8),
        ("prof_trade_6", "vet1", "wr1", 0, 9),
        ("prof_trade_7", "vet1", "rb1", 0, 10),
        ("prof_trade_8", "vet1", "rookie1", 0, 11),
        ("prof_trade_9", "wr2", "rbb1", 0, 12),
        ("prof_trade_10", "wr2", "wrb1", 0, 13),
        ("prof_trade_11", "wr2", "te1", 0, 14),
        ("prof_trade_12", "wr2", "wr1", 0, 15),
    ]
    for index, (transaction_id, received, sent, sent_pick_round, week) in enumerate(trade_rows):
        draft_picks = (
            [
                {
                    "season": "2026",
                    "round": sent_pick_round,
                    "roster_id": 2,
                    "owner_id": 2,
                    "previous_owner_id": 1,
                }
            ]
            if sent_pick_round
            else []
        )
        phase2_seed_data.execute(
            """
            INSERT INTO transactions (
                transaction_id, league_id, type, status, created_at,
                roster_ids, adds, drops, draft_picks, week
            )
            VALUES (?, 'league_x', 'trade', 'complete', ?, ?, ?, ?, ?, ?)
            """,
            [
                transaction_id,
                base_time + timedelta(days=index),
                json.dumps([1, 2]),
                json.dumps({received: 1, sent: 2}),
                json.dumps({received: 2, sent: 1}),
                json.dumps(draft_picks),
                week,
            ],
        )
    return phase2_seed_data


@pytest.fixture
def trade_seed_data(profiling_seed_data):
    from fantasy.intelligence.intelligence_service import IntelligenceService
    from fantasy.profiling.profiling_engine import ProfilingEngine
    from fantasy.profiling.profiling_repo import ProfilingRepo

    conn = profiling_seed_data
    IntelligenceService(conn).compute_league("league_x")
    conn.execute(
        """
        UPDATE team_directions
        SET primary_label = 'hard_rebuild', confidence = 0.92
        WHERE league_id = 'league_x' AND roster_id = 1
        """
    )

    engine = ProfilingEngine(conn)
    repo = ProfilingRepo(conn)
    for profile in engine.compute_all_profiles("league_x"):
        repo.upsert_profile(profile)
        repo.replace_pitch_angles(profile.league_id, profile.roster_id, profile.pitch_angles)
    return conn
