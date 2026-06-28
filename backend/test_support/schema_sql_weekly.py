WEEKLY_SCHEMA_SQL = [
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
        overall_playoff_target  FLOAT,
        overall_title_target    FLOAT,
        overall_elite_target    FLOAT,
        overall_gap_to_playoff_target FLOAT,
        overall_gap_to_title_target   FLOAT,
        overall_gap_to_elite_target   FLOAT,
        overall_benchmark_source      VARCHAR,
        overall_benchmark_sample_size INTEGER,
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
