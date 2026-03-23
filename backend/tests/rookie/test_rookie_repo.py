from __future__ import annotations

import json

from fantasy.rookie.rookie_repo import RookieRepo


def _seed_rookie_data(conn) -> None:
    conn.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions,
            settings_blob, superflex, tep, ppr
        )
        VALUES (
            'league_rookie',
            'Rookie League',
            '2026',
            '{"rec":1.0}',
            '["QB","RB","WR","TE","SUPER_FLEX"]',
            '{"num_teams":12}',
            TRUE,
            TRUE,
            1.0
        )
        """
    )
    conn.execute(
        """
        INSERT INTO rosters (
            id, league_id, roster_id, owner_id, owner_display_name, starters, players, reserve, taxi
        )
        VALUES
            (1, 'league_rookie', 1, 'owner_a', 'Alpha', '[]', '[]', '[]', '[]'),
            (2, 'league_rookie', 2, 'owner_b', 'Beta', '[]', '[]', '[]', '[]')
        """
    )

    players = [
        ("qb_rookie", "QB Prospect", "QB", "A", 22, {"draft_year": 2026, "mobile": True, "draft_pick": 8}),
        ("wr_elite", "Elite WR", "WR", "B", 21, {"draft_year": 2026, "forty": 4.42, "target_share": 0.3, "draft_pick": 5}),
        ("wr_slot", "Slot WR", "WR", "C", 22, {"draft_year": 2026, "slot_rate": 0.65, "draft_pick": 28}),
        ("rb_workhorse", "Power RB", "RB", "D", 22, {"draft_year": 2026, "weight": 220, "draft_pick": 20}),
        ("te_move", "Move TE", "TE", "E", 22, {"draft_year": 2026, "move_te": True, "draft_pick": 18}),
        ("wr_longshot", "Longshot WR", "WR", "F", 24, {"draft_year": 2026, "injury_flag": True, "draft_pick": 150}),
    ]
    for index, (player_id, full_name, position, team, age, metadata) in enumerate(players, start=1):
        conn.execute(
            """
            INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [player_id, full_name, position, team, age, json.dumps(metadata)],
        )
        conn.execute(
            """
            INSERT INTO player_adp_baseline (player_id, player_name, position, adp, adp_source)
            VALUES (?, ?, ?, ?, 'test')
            """,
            [player_id, full_name, position, float(index)],
        )


def test_get_league_settings_reads_format_flags(db):
    _seed_rookie_data(db)
    repo = RookieRepo(db)
    settings = repo.get_league_settings("league_rookie")
    assert settings["superflex"] is True
    assert settings["tep"] is True
    assert settings["ppr"] == 1.0
    assert settings["league_size"] == 12


def test_get_available_rookies_returns_current_class(db):
    _seed_rookie_data(db)
    repo = RookieRepo(db)
    rookies = repo.get_available_rookies("league_rookie")
    assert len(rookies) == 6
    assert rookies[0]["player_id"] == "qb_rookie"
    assert all(player["metadata"]["draft_year"] == 2026 for player in rookies)


def test_save_board_cache_and_tendencies_round_trip(db):
    _seed_rookie_data(db)
    repo = RookieRepo(db)
    repo.save_board_cache("league_rookie", 0.25, '{"tiers":[]}')
    repo.replace_league_tendencies(
        "league_rookie",
        [
            {
                "tendency_type": "positional_run",
                "position": "WR",
                "player_id": None,
                "player_name": None,
                "early_draft_slots": 1.5,
                "adp_delta": None,
                "system_value_slot": None,
            }
        ],
    )
    row = db.execute(
        "SELECT class_strength_signal FROM rookie_board_cache WHERE league_id = 'league_rookie'"
    ).fetchone()
    tendencies = repo.get_league_tendencies("league_rookie")
    assert row == (0.25,)
    assert tendencies[0]["position"] == "WR"
