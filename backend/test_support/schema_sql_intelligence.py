FRESH_INTELLIGENCE_SCHEMA_SQL = [
    """
    CREATE TABLE IF NOT EXISTS intelligence_source_runs (
        run_id VARCHAR PRIMARY KEY, trigger VARCHAR NOT NULL, status VARCHAR NOT NULL,
        started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, completed_at TIMESTAMP,
        source_outcomes_json VARCHAR NOT NULL DEFAULT '[]', event_count INTEGER NOT NULL DEFAULT 0,
        impact_count INTEGER NOT NULL DEFAULT 0, brief_id VARCHAR, error_message VARCHAR
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS source_observations (
        observation_id VARCHAR PRIMARY KEY, run_id VARCHAR NOT NULL, source_id VARCHAR NOT NULL,
        source_tier VARCHAR NOT NULL, url VARCHAR, fetched_at TIMESTAMP NOT NULL,
        observed_at TIMESTAMP, effective_at TIMESTAMP, coverage_through TIMESTAMP,
        content_hash VARCHAR NOT NULL, parse_status VARCHAR NOT NULL, evidence_excerpt VARCHAR,
        payload_json VARCHAR NOT NULL, authoritative BOOLEAN NOT NULL DEFAULT FALSE,
        model_extracted BOOLEAN NOT NULL DEFAULT FALSE, UNIQUE (source_id, content_hash)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS football_events (
        event_id VARCHAR PRIMARY KEY, fingerprint VARCHAR NOT NULL UNIQUE,
        subject_key VARCHAR NOT NULL, event_type VARCHAR NOT NULL, player_id VARCHAR,
        player_name VARCHAR, team VARCHAR, effective_at TIMESTAMP, observed_at TIMESTAMP NOT NULL,
        expires_at TIMESTAMP, verification_state VARCHAR NOT NULL, confidence DOUBLE NOT NULL,
        summary VARCHAR NOT NULL, details_json VARCHAR NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS event_evidence (
        event_id VARCHAR NOT NULL, observation_id VARCHAR NOT NULL,
        linked_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (event_id, observation_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS event_reviews (
        review_id VARCHAR PRIMARY KEY, event_id VARCHAR NOT NULL, decision VARCHAR NOT NULL,
        notes VARCHAR, reviewed_by VARCHAR NOT NULL DEFAULT 'user',
        reviewed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS canonical_player_projections (
        projection_id VARCHAR PRIMARY KEY, event_id VARCHAR NOT NULL,
        league_id VARCHAR NOT NULL, player_id VARCHAR NOT NULL,
        availability_before VARCHAR, availability_after VARCHAR,
        role_before DOUBLE, role_after DOUBLE, value_before DOUBLE NOT NULL,
        value_after DOUBLE NOT NULL, delta_json VARCHAR NOT NULL DEFAULT '{}',
        confidence DOUBLE NOT NULL, invalidation VARCHAR NOT NULL,
        model_version VARCHAR NOT NULL,
        computed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (event_id, league_id, player_id, model_version)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS league_impacts (
        impact_id VARCHAR PRIMARY KEY, event_id VARCHAR NOT NULL, league_id VARCHAR NOT NULL,
        roster_id INTEGER, impact_type VARCHAR NOT NULL,
        affected_asset_ids_json VARCHAR NOT NULL DEFAULT '[]', headline VARCHAR NOT NULL,
        explanation VARCHAR NOT NULL, before_json VARCHAR NOT NULL DEFAULT '{}',
        after_json VARCHAR NOT NULL DEFAULT '{}', deltas_json VARCHAR NOT NULL DEFAULT '{}',
        confidence DOUBLE NOT NULL, actionable BOOLEAN NOT NULL DEFAULT FALSE,
        recommended_action VARCHAR, cta_label VARCHAR, cta_destination VARCHAR,
        invalidation VARCHAR NOT NULL, model_version VARCHAR NOT NULL,
        computed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS daily_briefs (
        brief_id VARCHAR PRIMARY KEY, brief_date DATE NOT NULL, content_hash VARCHAR NOT NULL,
        run_id VARCHAR NOT NULL,
        status VARCHAR NOT NULL, source_health_json VARCHAR NOT NULL DEFAULT '[]',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (brief_date, content_hash)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS daily_brief_items (
        item_id VARCHAR PRIMARY KEY, brief_id VARCHAR NOT NULL, event_id VARCHAR NOT NULL,
        league_id VARCHAR, roster_id INTEGER, lane VARCHAR NOT NULL, priority_rank INTEGER NOT NULL,
        headline VARCHAR NOT NULL, why_it_matters VARCHAR NOT NULL, recommended_action VARCHAR,
        confidence DOUBLE NOT NULL, source_summary VARCHAR NOT NULL, invalidation VARCHAR NOT NULL,
        impact_json VARCHAR NOT NULL DEFAULT '{}', cta_label VARCHAR, cta_destination VARCHAR,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS brief_feedback (
        feedback_id VARCHAR PRIMARY KEY, brief_id VARCHAR NOT NULL, item_id VARCHAR NOT NULL,
        verdict VARCHAR NOT NULL, notes VARCHAR,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
]
