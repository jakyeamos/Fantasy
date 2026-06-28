CORE_SCHEMA_SQL = [
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
        trend_result_json VARCHAR,
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
]
