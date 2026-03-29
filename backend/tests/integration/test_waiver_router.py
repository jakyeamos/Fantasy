from __future__ import annotations

import json

from fastapi.testclient import TestClient

from fantasy.main import create_app
from fantasy.routers.deps import get_read_db_conn, get_write_db_conn


def _override_conn(conn):
    def _getter():
        yield conn

    return _getter


def _seed_phase15_router_data(conn) -> None:
    conn.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions,
            settings_blob, superflex, tep, ppr
        )
        VALUES (
            'phase15_x',
            'Phase 15 League',
            '2026',
            '{}',
            '["QB","RB","WR","TE","SUPER_FLEX","BN"]',
            '{"waiver_budget":100,"waiver_type":2}',
            TRUE,
            FALSE,
            1.0
        )
        """
    )
    conn.execute(
        """
        INSERT INTO rosters (
            id, league_id, roster_id, owner_id, owner_display_name, waiver_position,
            waiver_budget_used, starters, players, reserve, taxi
        )
        VALUES
            (1, 'phase15_x', 1, 'owner_a', 'Alpha', 2, 35, '["qb1","rb1","wr1"]', '["qb1","rb1","wr1"]', '[]', '[]'),
            (2, 'phase15_x', 2, 'owner_b', 'Beta', 7, 10, '["o1","o2","o3"]', '["o1","o2","o3"]', '[]', '[]')
        """
    )
    conn.execute(
        """
        INSERT INTO team_directions (
            id, league_id, roster_id, primary_label, confidence, reasoning,
            alternates_json, delta_json, approved_moves, discouraged_moves
        )
        VALUES
            (1, 'phase15_x', 1, 'hard_rebuild', 0.9, 'seeded', '[]', '{}', '["sell_veterans","acquire_future_first"]', '[]')
        """
    )
    for player_id, name, position, age, metadata in [
        ("qb1", "Roster QB", "QB", 30, {"status": "Active"}),
        ("rb1", "Roster RB", "RB", 29, {"status": "Active"}),
        ("wr1", "Roster WR", "WR", 31, {"status": "Active"}),
        ("o1", "Other One", "WR", 25, {"status": "Active"}),
        ("o2", "Other Two", "RB", 25, {"status": "Active"}),
        ("o3", "Other Three", "TE", 25, {"status": "Active"}),
        ("fa1", "Waiver One", "WR", 23, {"status": "Active"}),
        ("fa2", "Waiver Two", "RB", 24, {"status": "Active"}),
    ]:
        conn.execute(
            """
            INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
            VALUES (?, ?, ?, 'X', ?, ?)
            """,
            [player_id, name, position, age, json.dumps(metadata)],
        )
    conn.execute(
        """
        INSERT INTO player_values (
            id, league_id, roster_id, player_id,
            comp_current_production, comp_short_term, comp_role_stability,
            comp_age_curve, comp_insulation, comp_market_liquidity,
            comp_positional_scarcity, comp_fragility, comp_ceiling, comp_floor,
            comp_rerollability, comp_contract,
            lens_production, lens_market, lens_insulation, lens_team_fit, lens_direction
        )
        VALUES
            (1, 'phase15_x', 1, 'qb1', 0,0,0,10,0,0,55,0,0,0,0,0,0,70,0,0,0),
            (2, 'phase15_x', 1, 'rb1', 0,0,0,12,0,0,55,0,0,0,0,0,0,65,0,0,0),
            (3, 'phase15_x', 1, 'wr1', 0,0,0,15,0,0,55,0,0,0,0,0,0,50,0,0,0)
        """
    )
    conn.execute(
        """
        INSERT INTO player_stats_weekly (player_id, player_name, position, season, week, fantasy_points)
        VALUES
            ('fa1', 'Waiver One', 'WR', 2026, 1, 11.0),
            ('fa2', 'Waiver Two', 'RB', 2026, 1, 9.0)
        """
    )
    conn.execute(
        """
        INSERT INTO hygiene_suggestions (id, league_id, roster_id, suggestions_json)
        VALUES (
            1,
            'phase15_x',
            1,
            '[{"action_type":"cut","primary_player_ids":["wr1"],"primary_player_names":["Roster WR"],"reasoning":"Free the spot.","direction_fit_score":0.2}]'
        )
        """
    )
    conn.execute(
        """
        INSERT INTO lineup_scores (
            id, league_id, roster_id, total_lineup_score, title_window_label,
            title_window_composite, ceiling_score, stability_score, depth_score, slot_scores_json
        )
        VALUES
            (1, 'phase15_x', 1, 18.0, 'Window', 0, 0, 0, 0, '[]'),
            (2, 'phase15_x', 2, 55.0, 'Window', 0, 0, 0, 0, '[]')
        """
    )
    conn.execute(
        """
        INSERT INTO pick_values (
            id, league_id, pick_owner_roster_id, pick_year, pick_round,
            expected_draft_slot, base_value, timed_value, league_adjusted_value,
            demand_adjusted_value, timing_label, timing_reasoning
        )
        VALUES
            (1, 'phase15_x', 1, 2026, 1, 1.0, 50.0, 50.0, 50.0, 10.0, 'hold_until_rookie_fever', 'seed'),
            (2, 'phase15_x', 2, 2026, 1, 1.0, 50.0, 50.0, 50.0, 40.0, 'hold_until_rookie_fever', 'seed')
        """
    )


def test_waiver_recommendations_valid(db):
    _seed_phase15_router_data(db)
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(db)
    app.dependency_overrides[get_write_db_conn] = _override_conn(db)
    client = TestClient(app)

    response = client.get("/waiver/phase15_x/1/recommendations")
    assert response.status_code == 200
    payload = response.json()
    assert payload["recommendations"]
    assert payload["waiver_type_label"] == "faab"


def test_orphan_intake_endpoint(db):
    _seed_phase15_router_data(db)
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(db)
    app.dependency_overrides[get_write_db_conn] = _override_conn(db)
    client = TestClient(app)

    response = client.post("/waiver/phase15_x/1/orphan-intake")
    assert response.status_code == 200
    payload = response.json()
    assert "composite_score" in payload
    assert "age_curve" in payload


def test_action_plan_endpoint(db):
    _seed_phase15_router_data(db)
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(db)
    app.dependency_overrides[get_write_db_conn] = _override_conn(db)
    client = TestClient(app)

    response = client.get("/waiver/phase15_x/1/action-plan")
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"]
    assert any(item["category"] == "add" for item in payload["items"])
