from __future__ import annotations

import json

from fantasy.weekly.weekly_edge_service import WeeklyEdgeService


def test_weekly_edge_surfaces_start_sit_swap(db):
    db.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions,
            settings_blob, superflex, tep, ppr
        )
        VALUES ('weekly_x', 'Weekly League', '2026', '{}', '["WR","WR","BN"]', '{}', FALSE, FALSE, 1.0)
        """
    )
    db.execute(
        """
        INSERT INTO rosters (
            id, league_id, roster_id, owner_id, owner_display_name,
            starters, players, reserve, taxi
        )
        VALUES (
            1, 'weekly_x', 1, 'owner_a', 'Alpha',
            '["wr_cold"]', '["wr_cold","wr_hot"]', '[]', '[]'
        )
        """
    )
    for player_id, name in [("wr_cold", "Cold Starter"), ("wr_hot", "Hot Bench")]:
        db.execute(
            """
            INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
            VALUES (?, ?, 'WR', 'X', 25, ?)
            """,
            [player_id, name, json.dumps({"status": "Active"})],
        )
    db.execute(
        """
        INSERT INTO player_stats_weekly (
            player_id, player_name, position, season, week, fantasy_points, targets, carries
        )
        VALUES
            ('wr_cold', 'Cold Starter', 'WR', 2026, 1, 4.0, 3.0, 0.0),
            ('wr_cold', 'Cold Starter', 'WR', 2026, 2, 5.0, 4.0, 0.0),
            ('wr_hot', 'Hot Bench', 'WR', 2026, 1, 13.0, 8.0, 0.0),
            ('wr_hot', 'Hot Bench', 'WR', 2026, 2, 14.0, 9.0, 0.0)
        """
    )

    result = WeeklyEdgeService(db).build("weekly_x", 1)

    assert result.start_sit
    top = result.start_sit[0]
    assert top.start_player_name == "Hot Bench"
    assert top.sit_player_name == "Cold Starter"
    assert top.confidence in {"HIGH", "MEDIUM"}

