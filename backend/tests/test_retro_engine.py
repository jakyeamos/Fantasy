from __future__ import annotations

from fantasy.portfolio.retro_engine import RetroEngine


def _seed_direction_case(conn, label: str, wins: int, losses: int, league_id: str = "league_x") -> None:
    conn.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions, settings_blob, superflex, tep, ppr
        )
        VALUES (?, ?, '2025', '{}', '[]', '{"num_teams":2}', FALSE, FALSE, 0.0)
        """,
        [league_id, league_id],
    )
    conn.execute(
        """
        INSERT INTO standings (id, league_id, roster_id, wins, losses, ties, fpts, fpts_against)
        VALUES (1, ?, 1, ?, ?, 0, 0, 0)
        """,
        [league_id, wins, losses],
    )
    conn.execute(
        """
        INSERT INTO team_directions (
            id, league_id, roster_id, primary_label, confidence, reasoning, alternates_json,
            delta_json, approved_moves, discouraged_moves
        )
        VALUES (1, ?, 1, ?, 0.8, 'reason', '[]', '{}', '[]', '[]')
        """,
        [league_id, label],
    )


def test_grade_direction_labels_contender_correct(db):
    _seed_direction_case(db, "true_contender", 10, 4)

    result = RetroEngine(db).grade_direction_labels("2025")

    assert result["overall_accuracy"] == 1.0
    assert result["by_label"]["true_contender"]["correct"] == 1


def test_grade_direction_labels_rebuild_correct(db):
    _seed_direction_case(db, "hard_rebuild", 3, 11)

    result = RetroEngine(db).grade_direction_labels("2025")

    assert result["overall_accuracy"] == 1.0
    assert result["by_label"]["hard_rebuild"]["correct"] == 1


def test_grade_direction_labels_contender_wrong(db):
    _seed_direction_case(db, "true_contender", 3, 11)

    result = RetroEngine(db).grade_direction_labels("2025")

    assert result["overall_accuracy"] == 0.0
    assert result["by_label"]["true_contender"]["correct"] == 0


def test_grade_prospect_tiers_table_missing(db):
    result = RetroEngine(db).grade_prospect_tiers("2025")

    assert result["status"] == "skipped"


def test_grade_prospect_tiers_basic(db):
    db.execute(
        """
        CREATE TABLE prospect_model_outputs (
            player_id VARCHAR NOT NULL,
            position VARCHAR NOT NULL,
            predicted_tier INTEGER NOT NULL,
            predicted_bucket VARCHAR NOT NULL,
            draft_season VARCHAR NOT NULL
        )
        """
    )
    db.execute(
        """
        INSERT INTO prospect_model_outputs (player_id, position, predicted_tier, predicted_bucket, draft_season)
        VALUES ('rookie_hit', 'WR', 1, 'hit', '2025')
        """
    )
    db.execute(
        """
        INSERT INTO player_stats_weekly (
            player_id, player_name, position, season, week, fantasy_points
        )
        VALUES
            ('rookie_hit', 'Rookie Hit', 'WR', 2025, 1, 120),
            ('rookie_hit', 'Rookie Hit', 'WR', 2025, 2, 130)
        """
    )

    result = RetroEngine(db).grade_prospect_tiers("2025")

    assert result["status"] == "ok"
    assert result["overall_accuracy"] == 1.0
