from __future__ import annotations

import json

from fantasy.context.context_repo import ContextRepo
from fantasy.context.freshness_service import FreshnessService
from fantasy.weekly.public_context import (
    WeeklyPublicContextService,
    ensure_weekly_context_schema,
)
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
    ensure_weekly_context_schema(db)
    db.execute(
        """
        INSERT INTO team_schedule_weekly (team, season, week, opponent, is_home, game_date, game_type)
        VALUES ('X', 2026, 3, 'Y', TRUE, '2026-09-20', 'REG')
        """
    )

    result = WeeklyEdgeService(db).build("weekly_x", 1)

    assert result.start_sit
    top = result.start_sit[0]
    assert top.start_player_name == "Hot Bench"
    assert top.sit_player_name == "Cold Starter"
    assert top.confidence in {"HIGH", "MEDIUM"}
    assert top.start_projection > top.sit_projection
    assert "vs Y" in top.why_now
    hot_signal = next(signal for signal in result.player_signals if signal.player_id == "wr_hot")
    assert hot_signal.opponent_team == "Y"
    assert hot_signal.projection_points > hot_signal.recent_points
    assert hot_signal.usage_note is not None


def test_weekly_edge_pushes_out_starter_below_active_bench(db):
    db.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions,
            settings_blob, superflex, tep, ppr
        )
        VALUES ('weekly_injury', 'Weekly Injury', '2026', '{}', '["RB","BN"]', '{}', FALSE, FALSE, 1.0)
        """
    )
    db.execute(
        """
        INSERT INTO rosters (
            id, league_id, roster_id, owner_id, owner_display_name,
            starters, players, reserve, taxi
        )
        VALUES (
            2, 'weekly_injury', 1, 'owner_a', 'Alpha',
            '["rb_out"]', '["rb_out","rb_active"]', '[]', '[]'
        )
        """
    )
    players = [
        ("rb_out", "Out Starter", "Out"),
        ("rb_active", "Active Bench", "Active"),
        ("opp_rb", "Opponent RB", "Active"),
    ]
    for player_id, name, status in players:
        team = "Y" if player_id == "opp_rb" else "X"
        db.execute(
            """
            INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
            VALUES (?, ?, 'RB', ?, 25, ?)
            """,
            [player_id, name, team, json.dumps({"status": status})],
        )
    db.execute(
        """
        INSERT INTO player_stats_weekly (
            player_id, player_name, position, season, week, fantasy_points, carries
        )
        VALUES
            ('rb_out', 'Out Starter', 'RB', 2026, 1, 12.0, 12.0),
            ('rb_active', 'Active Bench', 'RB', 2026, 1, 8.0, 10.0),
            ('opp_rb', 'Opponent RB', 'RB', 2026, 1, 20.0, 18.0)
        """
    )
    ensure_weekly_context_schema(db)
    db.execute(
        """
        INSERT INTO team_schedule_weekly (team, season, week, opponent, is_home, game_date, game_type)
        VALUES ('X', 2026, 3, 'Y', TRUE, '2026-09-20', 'REG')
        """
    )

    result = WeeklyEdgeService(db).build("weekly_injury", 1)

    top = result.start_sit[0]
    assert top.start_player_name == "Active Bench"
    assert top.sit_player_name == "Out Starter"
    starter = next(signal for signal in result.player_signals if signal.player_id == "rb_out")
    assert starter.availability_status == "out"
    assert starter.projection_points < starter.recent_points


def test_weekly_edge_does_not_replace_rookie_rb_with_free_agent_wr(db):
    db.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions,
            settings_blob, superflex, tep, ppr
        )
        VALUES ('weekly_rookie', 'Weekly Rookie', '2026', '{}', '["RB","WR","BN"]', '{}', FALSE, FALSE, 1.0)
        """
    )
    db.execute(
        """
        INSERT INTO rosters (
            id, league_id, roster_id, owner_id, owner_display_name,
            starters, players, reserve, taxi
        )
        VALUES (
            4, 'weekly_rookie', 1, 'owner_a', 'Alpha',
            '["rookie_rb","starting_wr"]', '["rookie_rb","starting_wr","fa_wr"]', '[]', '[]'
        )
        """
    )
    players = [
        ("rookie_rb", "Rookie RB", "RB", "NYG"),
        ("starting_wr", "Starting WR", "WR", "NYG"),
        ("fa_wr", "Free Agent WR", "WR", "FA"),
    ]
    for player_id, name, position, team in players:
        db.execute(
            """
            INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
            VALUES (?, ?, ?, ?, 25, ?)
            """,
            [player_id, name, position, team, json.dumps({"status": "Active"})],
        )
    db.execute(
        """
        INSERT INTO player_stats_weekly (
            player_id, player_name, position, season, week, fantasy_points, targets
        )
        VALUES
            ('starting_wr', 'Starting WR', 'WR', 2026, 1, 9.0, 7.0),
            ('fa_wr', 'Free Agent WR', 'WR', 2025, 16, 18.0, 10.0),
            ('fa_wr', 'Free Agent WR', 'WR', 2025, 17, 17.0, 10.0)
        """
    )
    ensure_weekly_context_schema(db)
    db.execute(
        """
        INSERT INTO team_schedule_weekly (team, season, week, opponent, is_home, game_date, game_type)
        VALUES ('NYG', 2026, 1, 'DAL', TRUE, '2026-09-10', 'REG')
        """
    )

    result = WeeklyEdgeService(db).build("weekly_rookie", 1)

    assert result.start_sit == []


def test_weekly_edge_surfaces_bye_and_depth_context(db):
    db.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions,
            settings_blob, superflex, tep, ppr
        )
        VALUES ('weekly_bye', 'Weekly Bye', '2026', '{}', '["WR"]', '{}', FALSE, FALSE, 1.0)
        """
    )
    db.execute(
        """
        INSERT INTO rosters (
            id, league_id, roster_id, owner_id, owner_display_name,
            starters, players, reserve, taxi
        )
        VALUES (3, 'weekly_bye', 1, 'owner_a', 'Alpha', '["wr_bye"]', '["wr_bye"]', '[]', '[]')
        """
    )
    db.execute(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES (?, 'Bye WR', 'WR', 'BYE', 25, ?)
        """,
        [
            "wr_bye",
            json.dumps(
                {
                    "status": "Active",
                    "depth_chart_position": "WR",
                    "depth_chart_order": 2,
                }
            ),
        ],
    )
    db.execute(
        """
        INSERT INTO player_stats_weekly (
            player_id, player_name, position, season, week, fantasy_points, targets
        )
        VALUES ('wr_bye', 'Bye WR', 'WR', 2026, 1, 11.0, 8.0)
        """
    )
    ensure_weekly_context_schema(db)
    db.execute(
        """
        INSERT INTO team_schedule_weekly (team, season, week, opponent, is_home, game_date, game_type)
        VALUES ('OTHER', 2026, 3, 'Y', TRUE, '2026-09-20', 'REG')
        """
    )

    result = WeeklyEdgeService(db).build("weekly_bye", 1)

    signal = result.player_signals[0]
    assert signal.matchup_grade == "bye"
    assert signal.bye_week_warning is not None
    assert signal.role_note == "Depth context: WR, depth order 2."
    assert signal.projection_points < signal.recent_points


def test_weekly_context_refresh_marks_public_domains(db, monkeypatch):
    db.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions,
            settings_blob, superflex, tep, ppr
        )
        VALUES ('weekly_refresh', 'Weekly Refresh', '2026', '{}', '[]', '{}', FALSE, FALSE, 1.0)
        """
    )
    db.execute(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES ('wr1', 'Refresh WR', 'WR', 'BUF', 25, '{}')
        """
    )
    db.execute(
        """
        INSERT INTO player_stats_weekly (
            player_id, player_name, position, season, week, fantasy_points, targets
        )
        VALUES ('wr1', 'Refresh WR', 'WR', 2026, 1, 12.0, 8.0)
        """
    )
    service = WeeklyPublicContextService(db)
    monkeypatch.setattr(
        service,
        "_load_schedule_rows",
        lambda season: [
            {
                "team": "BUF",
                "season": season,
                "week": 1,
                "opponent": "MIA",
                "is_home": True,
                "game_date": "2026-09-10",
                "game_type": "REG",
            }
        ],
    )

    result = service.refresh("weekly_refresh", 2026)

    assert result.schedule_rows == 1
    assert set(result.refreshed_domains) == {"schedule", "stats"}
    tags = {
        tag.domain: tag
        for tag in FreshnessService(ContextRepo(db)).get_tags(
            "weekly_refresh", ["schedule", "stats", "injuries", "usage"]
        )
    }
    assert tags["schedule"].is_stale is False
    assert tags["stats"].is_stale is False
    assert tags["injuries"].is_stale is True
    assert tags["usage"].is_stale is True
    row = db.execute(
        "SELECT opponent FROM team_schedule_weekly WHERE team = 'BUF'"
    ).fetchone()
    assert row == ("MIA",)
