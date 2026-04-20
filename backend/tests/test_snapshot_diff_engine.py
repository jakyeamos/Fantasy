from __future__ import annotations

import json
from datetime import datetime, timedelta

from fantasy.portfolio.snapshot_diff_engine import SnapshotDiffEngine
from fantasy.picks.pick_engine import PickEngine


def _seed_league(conn) -> None:
    conn.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions, settings_blob, superflex, tep, ppr
        )
        VALUES ('league_x', 'League X', '2025', '{}', '[]', '{"num_teams":2}', FALSE, FALSE, 0.0)
        """
    )
    conn.execute(
        """
        INSERT INTO rosters (id, league_id, roster_id, owner_id, players, starters, reserve, taxi)
        VALUES
            (1, 'league_x', 1, 'user_a', '["player_a"]', '[]', '[]', '[]'),
            (2, 'league_x', 2, 'user_b', '["player_b"]', '[]', '[]', '[]')
        """
    )


def test_load_anchors_trade(db):
    _seed_league(db)
    snapshot_at = datetime(2025, 2, 14, 12, 0, 0)
    db.execute(
        """
        INSERT INTO league_snapshots (id, league_id, snapshot_at, snapshot_type, triggered_by, payload_json)
        VALUES (?, 'league_x', ?, 'delta', 'manual', ?)
        """,
        [
            1,
            snapshot_at,
            json.dumps({"state": {"season": "2025", "rosters": []}, "delta": {"changed_rosters": [1]}}),
        ],
    )
    db.execute(
        """
        INSERT INTO transactions (
            transaction_id, league_id, type, status, created_at, roster_ids, adds, drops, draft_picks, week
        )
        VALUES ('trade_1', 'league_x', 'trade', 'complete', ?, '[1,2]', '{}', '{}', '[]', 8)
        """,
        [snapshot_at + timedelta(minutes=20)],
    )

    anchors = SnapshotDiffEngine(db).load_anchors("league_x")

    assert any(anchor.anchor_type == "trade" for anchor in anchors)
    assert any(anchor.label == "Trade - Feb 14, 2025" for anchor in anchors)


def test_load_anchors_roster_change(db):
    _seed_league(db)
    db.execute(
        """
        INSERT INTO league_snapshots (id, league_id, snapshot_at, snapshot_type, triggered_by, payload_json)
        VALUES
            (1, 'league_x', ?, 'delta', 'manual', ?),
            (2, 'league_x', ?, 'delta', 'manual', ?)
        """,
        [
            datetime(2025, 1, 8, 9, 0, 0),
            json.dumps({"state": {"season": "2025", "rosters": []}, "delta": {"changed_rosters": [1, 2, 3, 4]}}),
            datetime(2025, 1, 9, 9, 0, 0),
            json.dumps({"state": {"season": "2025", "rosters": []}, "delta": {"changed_rosters": [1]}}),
        ],
    )

    anchors = SnapshotDiffEngine(db).load_anchors("league_x")

    assert any(anchor.anchor_type == "roster_change" for anchor in anchors)
    assert not any(
        anchor.snapshot_id == 2 and anchor.anchor_type == "roster_change"
        for anchor in anchors
    )


def test_load_anchors_season_checkpoint(db):
    _seed_league(db)
    db.execute(
        """
        INSERT INTO league_snapshots (id, league_id, snapshot_at, snapshot_type, triggered_by, payload_json)
        VALUES
            (1, 'league_x', ?, 'full', 'manual', ?),
            (2, 'league_x', ?, 'full', 'manual', ?)
        """,
        [
            datetime(2025, 9, 3, 9, 0, 0),
            json.dumps({"state": {"season": "2025", "rosters": []}}),
            datetime(2025, 12, 30, 9, 0, 0),
            json.dumps({"state": {"season": "2025", "rosters": []}}),
        ],
    )

    anchors = SnapshotDiffEngine(db).load_anchors("league_x")

    labels = {anchor.label for anchor in anchors}
    assert "Season start - Sep 03, 2025" in labels
    assert "Season end - Dec 30, 2025" in labels


def test_compute_diff_direction_change(db):
    _seed_league(db)
    snapshot_payload = {
        "state": {
            "season": "2025",
            "rosters": [
                {
                    "roster_id": 1,
                    "direction": {"label": "true_contender"},
                    "scorecard": {"win_now": 0.50},
                    "player_values": [],
                    "capital_score": 50.0,
                }
            ],
        }
    }
    db.execute(
        """
        INSERT INTO league_snapshots (id, league_id, snapshot_at, snapshot_type, triggered_by, payload_json)
        VALUES (1, 'league_x', ?, 'full', 'manual', ?)
        """,
        [datetime(2025, 9, 3, 9, 0, 0), json.dumps(snapshot_payload)],
    )
    db.execute(
        """
        INSERT INTO team_directions (
            id, league_id, roster_id, primary_label, confidence, reasoning, alternates_json,
            delta_json, approved_moves, discouraged_moves
        )
        VALUES (1, 'league_x', 1, 'retool', 0.8, 'reason', '[]', '{}', '[]', '[]')
        """
    )
    db.execute(
        """
        INSERT INTO team_scorecards (
            id, league_id, roster_id, win_now, future_value, depth, pick_capital, flexibility,
            fragility, age_risk, liquidity, positional_insulation, composite, computation_json
        )
        VALUES (1, 'league_x', 1, 0.62, 0.40, 0.40, 0.30, 0.40, 0.40, 0.40, 0.40, 0.40, 0.42, '{}')
        """
    )

    rows = SnapshotDiffEngine(db).compute_diff("league_x", 1, 1)

    assert any(row.field_type == "direction_label" for row in rows)


def test_compute_diff_player_departed(db):
    _seed_league(db)
    db.execute(
        """
        INSERT INTO players (player_id, full_name, position, team, metadata_blob)
        VALUES ('player_a', 'Player A', 'WR', 'SF', '{}')
        """
    )
    snapshot_at = datetime(2025, 9, 3, 9, 0, 0)
    snapshot_payload = {
        "state": {
            "season": "2025",
            "rosters": [
                {
                    "roster_id": 1,
                    "direction": {"label": "retool"},
                    "scorecard": {"win_now": 0.50},
                    "player_values": [
                        {
                            "player_id": "player_a",
                            "player_name": "Player A",
                            "position": "WR",
                            "lens_market": 0.45,
                        }
                    ],
                    "capital_score": 50.0,
                }
            ],
        }
    }
    db.execute(
        """
        INSERT INTO league_snapshots (id, league_id, snapshot_at, snapshot_type, triggered_by, payload_json)
        VALUES (1, 'league_x', ?, 'full', 'manual', ?)
        """,
        [snapshot_at, json.dumps(snapshot_payload)],
    )
    db.execute(
        """
        INSERT INTO transactions (
            transaction_id, league_id, type, status, created_at, roster_ids, adds, drops, draft_picks, week
        )
        VALUES ('trade_depart', 'league_x', 'trade', 'complete', ?, '[1,2]', '{"player_a":2}', '{"player_a":1}', '[]', 10)
        """,
        [snapshot_at + timedelta(days=1)],
    )
    db.execute(
        """
        UPDATE rosters
        SET players = '[]'
        WHERE league_id = 'league_x' AND roster_id = 1
        """
    )
    db.execute(
        """
        INSERT INTO team_scorecards (
            id, league_id, roster_id, win_now, future_value, depth, pick_capital, flexibility,
            fragility, age_risk, liquidity, positional_insulation, composite, computation_json
        )
        VALUES (1, 'league_x', 1, 0.50, 0.40, 0.40, 0.30, 0.40, 0.40, 0.40, 0.40, 0.40, 0.42, '{}')
        """
    )

    rows = SnapshotDiffEngine(db).compute_diff("league_x", 1, 1)

    departed = next(row for row in rows if row.field_type == "departed")
    assert departed.display_string == "Traded (was WR)"


def test_compute_diff_uses_roster_membership_for_adds_and_departures(db):
    _seed_league(db)
    db.execute(
        """
        INSERT INTO players (player_id, full_name, position, team, metadata_blob)
        VALUES
            ('player_a', 'Player A', 'WR', 'SF', '{}'),
            ('player_b', 'Player B', 'RB', 'DET', '{}')
        """
    )
    snapshot_payload = {
        "state": {
            "season": "2025",
            "rosters": [
                {
                    "roster_id": 1,
                    "players": ["player_a"],
                    "direction": {"label": "retool"},
                    "scorecard": {"win_now": 0.50},
                    "player_values": [
                        {
                            "player_id": "player_a",
                            "player_name": "Player A",
                            "position": "WR",
                            "lens_market": 0.45,
                        }
                    ],
                    "capital_score": 50.0,
                }
            ],
        }
    }
    db.execute(
        """
        INSERT INTO league_snapshots (id, league_id, snapshot_at, snapshot_type, triggered_by, payload_json)
        VALUES (1, 'league_x', ?, 'full', 'manual', ?)
        """,
        [datetime(2025, 9, 3, 9, 0, 0), json.dumps(snapshot_payload)],
    )
    db.execute(
        """
        UPDATE rosters
        SET players = '["player_b"]'
        WHERE league_id = 'league_x' AND roster_id = 1
        """
    )
    db.execute(
        """
        INSERT INTO player_values (
            id, league_id, roster_id, player_id, lens_market, lens_direction, lens_team_fit,
            comp_short_term, comp_age_curve, computed_at
        )
        VALUES (1, 'league_x', 1, 'player_a', 0.45, 0.40, 0.40, 0.40, 0.40, CURRENT_TIMESTAMP)
        """
    )

    rows = SnapshotDiffEngine(db).compute_diff("league_x", 1, 1)

    assert any(row.field_type == "departed" and row.field == "Player A" for row in rows)
    assert any(row.field_type == "added" and row.field == "Player B" for row in rows)


def test_compute_diff_pick_capital(db, monkeypatch):
    _seed_league(db)
    snapshot_payload = {
        "state": {
            "season": "2025",
            "rosters": [
                {
                    "roster_id": 1,
                    "direction": {"label": "retool"},
                    "scorecard": {"win_now": 0.50},
                    "player_values": [],
                    "capital_score": 50.0,
                }
            ],
        }
    }
    db.execute(
        """
        INSERT INTO league_snapshots (id, league_id, snapshot_at, snapshot_type, triggered_by, payload_json)
        VALUES (1, 'league_x', ?, 'full', 'manual', ?)
        """,
        [datetime(2025, 9, 3, 9, 0, 0), json.dumps(snapshot_payload)],
    )
    db.execute(
        """
        INSERT INTO team_scorecards (
            id, league_id, roster_id, win_now, future_value, depth, pick_capital, flexibility,
            fragility, age_risk, liquidity, positional_insulation, composite, computation_json
        )
        VALUES (1, 'league_x', 1, 0.50, 0.40, 0.40, 0.30, 0.40, 0.40, 0.40, 0.40, 0.40, 0.42, '{}')
        """
    )

    monkeypatch.setattr(PickEngine, "compute_capital_score", lambda self, league_id, roster_id: 68.0)

    rows = SnapshotDiffEngine(db).compute_diff("league_x", 1, 1)

    pick_capital = next(row for row in rows if row.field_type == "pick_capital")
    assert pick_capital.delta == 18.0
    assert pick_capital.display_string == "↑18 pts"
