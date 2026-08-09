from fantasy.capabilities import build_capability_manifest


def test_manifest_distinguishes_native_from_available_data(db):
    manifest = build_capability_manifest(db)
    capabilities = manifest["capabilities"]

    assert manifest["schema_version"] == "fantasy-agent-capabilities/1.0"
    assert capabilities["decision_packet"]["provider"] == "native"
    assert capabilities["decision_packet"]["runtime_state"] == "available"
    assert capabilities["external_market_values"]["runtime_state"] == "degraded"
    assert capabilities["external_market_values"]["latest_fetched_at"] is None
    assert capabilities["external_market_values"]["latest_refresh"] is None
    assert capabilities["decision_feedback"]["presented_events"] == 0
    assert capabilities["decision_feedback"]["labeled_outcomes"] == 0
    assert capabilities["decision_followups"]["runtime_state"] == "available"
    assert capabilities["decision_followups"]["unresolved_decisions"] == 0
    assert capabilities["decision_calibration"]["runtime_state"] == "unavailable"
    assert capabilities["decision_calibration"]["evidence"]["minimum_sample_size"] == 20
    assert capabilities["stats_integrity_gate"]["runtime_state"] == "unavailable"
    assert capabilities["golden_agent_evaluations"]["runtime_state"] == "verification_required"


def test_manifest_reports_degraded_stats_by_league(db):
    db.execute(
        """
        INSERT INTO leagues
            (league_id, name, season, scoring_settings, roster_positions, settings_blob)
        VALUES ('l1', 'League', '2026', '{}', '[]', '{}')
        """
    )
    db.execute(
        """
        INSERT INTO player_stats_weekly
            (player_id, player_name, position, season, week, fantasy_points,
             targets, carries, passing_yards, receiving_yards, rushing_yards)
        SELECT 'p' || player_no, 'Player ' || player_no, 'WR', 2025, week,
               player_no + week, week, player_no, 0, player_no + week, 0
        FROM range(1, 21) players(player_no)
        CROSS JOIN range(1, 7) weeks(week)
        """
    )
    db.execute(
        "INSERT INTO player_stats_weekly SELECT * REPLACE (2026 AS season) FROM player_stats_weekly WHERE season = 2025"
    )

    capabilities = build_capability_manifest(db)["capabilities"]

    assert capabilities["stats_integrity_gate"]["runtime_state"] == "degraded"
    assert (
        capabilities["stats_integrity_gate"]["league_health"]["l1"]["integrity_status"]
        == "blocked_by_integrity_failure"
    )


def test_manifest_reports_market_freshness_and_decision_lifecycle_counts(db):
    db.execute(
        """
        INSERT INTO market_values (id, player_id, fetched_at, fantasycalc_value)
        VALUES (1, 'p1', TIMESTAMP '2026-08-04 12:00:00', 8000)
        """
    )
    db.executemany(
        """
        INSERT INTO market_refresh_runs (
            id, run_at, source, num_qbs, num_teams, ppr, status,
            source_rows, matched_rows, matched_unique_rows, unmatched_rows,
            market_value_rows, coverage_ratio, error_detail
        ) VALUES (?, ?, 'fantasycalc_api', 2, 12, 0.5, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            [1, "2026-08-04 11:00:00", "success", 475, 347, 347, 128, 347, 0.7305, None],
            [2, "2026-08-04 13:00:00", "failure", 0, 0, 0, 0, 0, 0.0, "network unavailable"],
        ],
    )
    packet = '{"schema_version":"decision-packet/1.0"}'
    db.executemany(
        """
        INSERT INTO decision_feedback (
            id, decision_id, league_id, roster_id, packet_version,
            recommendation_action, confidence, event_type, action_taken,
            outcome, outcome_score, follow_up_at, resolution_state, packet_json
        ) VALUES (?, 'd1', 'l1', 1, 'decision-packet/1.0', 'hold', 0.7, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            [1, "presented", "presented", None, None, "2026-08-10", "awaiting_action", packet],
            [2, "accepted", "accepted", None, None, "2026-09-10", "awaiting_outcome", packet],
            [3, "outcome", "outcome", "worked", 1.0, "2026-09-10", "resolved", packet],
        ],
    )

    capabilities = build_capability_manifest(db)["capabilities"]

    assert capabilities["external_market_values"]["latest_fetched_at"] == "2026-08-04 12:00:00"
    assert capabilities["external_market_values"]["latest_refresh"]["id"] == 1
    assert capabilities["external_market_values"]["latest_refresh"]["coverage_ratio"] == 0.7305
    assert capabilities["external_market_values"]["latest_attempt"]["id"] == 2
    assert capabilities["external_market_values"]["latest_attempt"]["status"] == "failure"
    assert capabilities["decision_feedback"]["presented_events"] == 1
    assert capabilities["decision_feedback"]["action_events"] == 1
    assert capabilities["decision_feedback"]["labeled_outcomes"] == 1
    assert capabilities["decision_followups"]["unresolved_decisions"] == 0
    assert capabilities["decision_calibration"]["evidence"]["sample_size"] == 1
