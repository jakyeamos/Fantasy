from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from fantasy.waiver.waiver_engine import (
    WaiverEngine,
    compute_bid_range,
    get_available_players,
    get_faab_state,
)


def _seed_waiver_context(db, *, waiver_type: int = 2, stale_hours: int = 1, direction: str = "true_contender") -> None:
    ingested_at = datetime.now(timezone.utc) - timedelta(hours=stale_hours)
    db.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions,
            settings_blob, superflex, tep, ppr, ingested_at
        )
        VALUES (?, 'Waiver League', '2026', '{}', ?, ?, TRUE, FALSE, 1.0, ?)
        """,
        [
            "waiver_x",
            json.dumps(["QB", "RB", "WR", "WR", "TE", "SUPER_FLEX", "BN"]),
            json.dumps({"waiver_budget": 100, "waiver_type": waiver_type}),
            ingested_at,
        ],
    )
    db.execute(
        """
        INSERT INTO rosters (
            id, league_id, roster_id, owner_id, owner_display_name, waiver_position,
            waiver_budget_used, starters, players, reserve, taxi, ingested_at
        )
        VALUES
            (1, 'waiver_x', 1, 'owner_a', 'Alpha', 3, 44, '["qb1","rb1","wr1"]', '["qb1","rb1","wr1"]', '[]', '[]', ?),
            (2, 'waiver_x', 2, 'owner_b', 'Beta', 8, 12, '["rb2","wr2","te2"]', '["rb2","wr2","te2"]', '[]', '[]', ?)
        """,
        [ingested_at, ingested_at],
    )
    db.execute(
        """
        INSERT INTO team_directions (
            id, league_id, roster_id, primary_label, confidence, reasoning,
            alternates_json, delta_json, approved_moves, discouraged_moves
        )
        VALUES
            (1, 'waiver_x', 1, ?, 0.9, 'seeded', '[]', '{}', '["buy"]', '[]'),
            (2, 'waiver_x', 2, 'hard_rebuild', 0.9, 'seeded', '[]', '{}', '[]', '[]')
        """,
        [direction],
    )
    for player_id, name, position, age, metadata in [
        ("qb1", "Roster QB", "QB", 27, {}),
        ("rb1", "Roster RB", "RB", 26, {}),
        ("wr1", "Roster WR", "WR", 25, {}),
        ("rb2", "Other RB", "RB", 24, {}),
        ("wr2", "Other WR", "WR", 25, {}),
        ("te2", "Other TE", "TE", 26, {}),
        ("fa1", "Free Agent One", "WR", 23, {"status": "Active"}),
        ("fa2", "Free Agent Two", "RB", 29, {"status": "Active"}),
        ("fa3", "Inactive Depth", "WR", 31, {"status": "Inactive"}),
    ]:
        db.execute(
            """
            INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
            VALUES (?, ?, ?, 'X', ?, ?)
            """,
            [player_id, name, position, age, json.dumps(metadata)],
        )
    db.execute(
        """
        INSERT INTO player_stats_weekly (player_id, player_name, position, season, week, fantasy_points)
        VALUES
            ('fa1', 'Free Agent One', 'WR', 2026, 1, 12.0),
            ('fa1', 'Free Agent One', 'WR', 2026, 2, 11.0),
            ('fa2', 'Free Agent Two', 'RB', 2026, 1, 7.0)
        """
    )
    db.execute(
        """
        INSERT INTO player_adp_baseline (player_id, player_name, position, adp, adp_source)
        VALUES
            ('fa1', 'Free Agent One', 'WR', 24.0, 'seed'),
            ('fa2', 'Free Agent Two', 'RB', 61.0, 'seed')
        """
    )


def test_faab_contender_bid():
    low, mid, high = compute_bid_range(85, 80, 70, 1.0, 50, True)
    assert low > 0
    assert low < mid < high <= 80


def test_faab_rebuild_bid():
    contender = compute_bid_range(85, 80, 70, 1.0, 50, True)
    rebuild = compute_bid_range(85, 80, 70, 0.30, 50, True)
    assert rebuild[2] < contender[2]


def test_free_agent_only_threshold():
    assert compute_bid_range(12, 80, 70, 1.0, 50, True) == (0, 0, 0)


def test_bid_ceiling_enforcement():
    _, _, high = compute_bid_range(90, 15, 15, 1.0, 80, True)
    assert high <= 15


def test_zero_budget():
    assert compute_bid_range(90, 0, 40, 1.0, 60, True) == (0, 0, 0)


def test_rolling_waiver_type(db):
    _seed_waiver_context(db, waiver_type=1)
    result = WaiverEngine(db).compute_recommendations("waiver_x", 1)
    assert result.waiver_type_label == "rolling"
    assert result.recommendations
    assert all(item.recommendation_label == "rolling_waiver" for item in result.recommendations)
    assert all(item.bid_low is None and item.bid_mid is None and item.bid_high is None for item in result.recommendations)


def test_free_agent_availability(db):
    _seed_waiver_context(db)
    available = get_available_players(db, "waiver_x")
    assert "fa1" in available
    assert "fa2" in available
    assert "qb1" not in available
    assert "fa3" not in available


def test_remaining_budget_calc(db):
    _seed_waiver_context(db)
    state = get_faab_state(db, "waiver_x", 1)
    assert state["remaining_faab"] == 56


def test_stale_data_warning(db):
    _seed_waiver_context(db, stale_hours=13)
    result = WaiverEngine(db).compute_recommendations("waiver_x", 1)
    assert result.data_freshness_warning is True
    assert all(item.data_freshness_warning for item in result.recommendations)
