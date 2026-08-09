from fantasy.data_health import assess_stats_health, resolve_stats_season


def _clone_stats_year(db, source: int, target: int) -> None:
    db.execute(
        """
        INSERT INTO player_stats_weekly
        SELECT player_id, player_name, position, ?, week, receptions, targets,
               receiving_yards, receiving_tds, rushing_yards, rushing_tds, carries,
               passing_yards, passing_tds, interceptions, passing_2pt_conversions,
               receiving_2pt_conversions, rushing_2pt_conversions, fantasy_points
        FROM player_stats_weekly
        WHERE season = ?
        """,
        [target, source],
    )


def test_valid_latest_available_season_is_selected(phase2_seed_data):
    health = assess_stats_health(phase2_seed_data, 2025)

    assert health.status == "valid"
    assert health.integrity_status == "passed"
    assert health.scoring_season == 2024
    assert health.scoring_status == "selected_valid"


def test_cross_season_clone_is_excluded_with_valid_fallback(db):
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
    _clone_stats_year(db, 2025, 2026)

    health = assess_stats_health(db, 2026)

    assert health.status == "degraded"
    assert health.integrity_status == "blocked_by_integrity_failure"
    assert health.scoring_season == 2025
    assert health.scoring_status == "fallback_valid"
    assert health.issues[0]["code"] == "cross_season_clone"
    assert health.issues[0]["identical_ratio"] == 1.0
    assert resolve_stats_season(db, 2026) == 2025


def test_small_identical_fixture_is_not_falsely_blocked(db):
    db.execute(
        """
        INSERT INTO player_stats_weekly
            (player_id, player_name, position, season, week, fantasy_points)
        VALUES ('p1', 'Player', 'WR', 2025, 1, 10),
               ('p1', 'Player', 'WR', 2026, 1, 10)
        """
    )

    health = assess_stats_health(db, 2026)

    assert health.status == "valid"
    assert health.scoring_season == 2026
