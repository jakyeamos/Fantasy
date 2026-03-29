from __future__ import annotations

from fastapi.testclient import TestClient

from fantasy.main import create_app
from fantasy.routers.deps import get_read_db_conn, get_write_db_conn


def _override_conn(conn):
    def _getter():
        yield conn

    return _getter


def _seed_startup_context(conn) -> None:
    conn.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions,
            settings_blob, superflex, tep, ppr
        )
        VALUES (
            'startup_x',
            'Startup League',
            '2026',
            '{}',
            '["QB","RB","WR","TE","SUPER_FLEX"]',
            '{}',
            TRUE,
            FALSE,
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
            (1, 'startup_x', 1, 'owner_a', 'Alpha', '[]', '[]', '[]', '[]'),
            (2, 'startup_x', 2, 'owner_b', 'Beta', '[]', '[]', '[]', '[]')
        """
    )
    conn.execute(
        """
        INSERT INTO team_directions (
            id, league_id, roster_id, primary_label, confidence, reasoning,
            alternates_json, delta_json, approved_moves, discouraged_moves
        )
        VALUES (1, 'startup_x', 1, 'hard_rebuild', 0.9, 'seeded', '[]', '{}', '[]', '[]')
        """
    )
    conn.execute(
        """
        INSERT INTO draft_slots (
            id, league_id, draft_id, season, roster_id, confirmed_slot, status
        )
        VALUES
            (1, 'startup_x', 'draft_1', 2026, 1, 1, 'drafting'),
            (2, 'startup_x', 'draft_1', 2026, 2, 2, 'drafting')
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
            (1, 'startup_x', 1, 2026, 1, 1.0, 0, 0, 0, 88.0, 'hold_until_rookie_fever', 'seed'),
            (2, 'startup_x', 1, 2026, 2, 2.0, 0, 0, 0, 61.0, 'hold_until_rookie_fever', 'seed'),
            (3, 'startup_x', 1, 2026, 3, 3.0, 0, 0, 0, 58.0, 'hold_until_rookie_fever', 'seed'),
            (4, 'startup_x', 1, 2026, 4, 4.0, 0, 0, 0, 57.0, 'hold_until_rookie_fever', 'seed')
        """
    )


def test_startup_context_drafting_league(db):
    _seed_startup_context(db)
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(db)
    app.dependency_overrides[get_write_db_conn] = _override_conn(db)
    client = TestClient(app)

    response = client.get("/startup/startup_x/context?roster_id=1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["startup_mode_available"] is True
    assert payload["build_template"] == "rebuild"
    assert payload["pick_valuations"]
