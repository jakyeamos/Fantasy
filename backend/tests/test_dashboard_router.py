from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from fantasy.config import get_settings
from fantasy.main import create_app
from fantasy.routers.deps import get_read_db_conn, get_write_db_conn
from fantasy.routers.dashboard import (
    _build_exploit_windows,
    _derive_primary_weakness,
    _derive_summary_signal,
    _direction_note,
    _direction_read,
    _league_competition_rows,
)


def _override_conn(conn):
    def _getter():
        yield conn

    return _getter


def test_snapshot_trigger_and_status(phase3_seed_data):
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(phase3_seed_data)
    app.dependency_overrides[get_write_db_conn] = _override_conn(phase3_seed_data)
    client = TestClient(app)

    response = client.post("/snapshots/trigger")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert len(payload["snapshot_ids"]) == 1

    status = client.get("/snapshots/status")
    assert status.status_code == 200
    assert status.json()[0]["league_id"] == "league_x"
    assert status.json()[0]["last_snapshot_at"] is not None


def test_dashboard_summary_returns_league_card(phase3_seed_data):
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(phase3_seed_data)
    app.dependency_overrides[get_write_db_conn] = _override_conn(phase3_seed_data)
    client = TestClient(app)

    assert client.post("/intelligence/compute/league_x").status_code == 200
    assert client.post("/snapshots/trigger").status_code == 200

    response = client.get("/dashboard/summary")
    assert response.status_code == 200
    league = response.json()[0]
    assert league["league_id"] == "league_x"
    assert league["confidence_band"] in {"High", "Medium", "Low", "--"}
    assert league["direction_read"] in {"Clear", "Leaning", "Hybrid", "Tentative", "--"}
    assert isinstance(league["direction_alternates"], list)
    assert league["summary_signal"]
    assert league["primary_weakness"]
    assert league["top_exploit_window"] is not None


def test_dashboard_summary_signal_prefers_pick_capital_edge(phase3_seed_data):
    phase3_seed_data.execute("DELETE FROM team_scorecards WHERE league_id = 'league_x'")
    phase3_seed_data.execute(
        """
        INSERT INTO team_scorecards (
            id, league_id, roster_id, win_now, future_value, depth, pick_capital,
            flexibility, fragility, age_risk, liquidity, positional_insulation,
            composite, computation_json
        )
        VALUES
            (1, 'league_x', 1, 0.4, 0.5, 0.6, 1.0, 0.2, 0.1, 0.1, 0.7, 0.3, 0.5, '{}'),
            (2, 'league_x', 2, 0.8, 0.4, 0.3, 0.2, 0.6, 0.3, 0.3, 0.2, 0.5, 0.4, '{}')
        """
    )

    signal = _derive_summary_signal(
        phase3_seed_data,
        "league_x",
        1,
        (0.4, 0.5, 0.6, 1.0, 0.2, 0.1, 0.1, 0.7, 0.3),
    )
    assert signal == "Pick capital edge: 1st of 2 in this league."


def test_dashboard_flexibility_note_calls_out_dominant_position(phase3_seed_data):
    phase3_seed_data.execute(
        """
        UPDATE rosters
        SET starters = '["qb1","rb1","wr1","wr2"]',
            players = '["qb1","rb1","wr1","wr2","wrb1","rookie1"]',
            reserve = '[]',
            taxi = '[]'
        WHERE league_id = 'league_x' AND roster_id = 1
        """
    )

    note = _derive_primary_weakness(
        (0.5, 0.6, 0.7, 0.8, 0.1, 0.2, 0.3, 0.4, 0.9),
        conn=phase3_seed_data,
        league_id="league_x",
        roster_id=1,
    )
    assert note == "WRs are 4 of 6 starters/bench players (67%)."


def test_dashboard_primary_weakness_does_not_treat_low_fragility_as_bad():
    note = _derive_primary_weakness(
        (0.8, 0.8, 0.8, 0.8, 0.2, 0.1, 0.3, 0.8, 0.8),
    )

    assert note == "Position mix is skewed toward one position group."


def test_dashboard_primary_weakness_treats_high_fragility_as_bad():
    note = _derive_primary_weakness(
        (0.8, 0.8, 0.8, 0.8, 0.4, 0.9, 0.2, 0.8, 0.8),
    )

    assert note == "You have too many brittle weekly outcomes right now."


def test_dashboard_league_returns_risers_fallers_and_windows(phase3_seed_data):
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(phase3_seed_data)
    app.dependency_overrides[get_write_db_conn] = _override_conn(phase3_seed_data)
    client = TestClient(app)

    assert client.post("/intelligence/compute/league_x").status_code == 200
    assert client.post("/snapshots/trigger").status_code == 200

    phase3_seed_data.execute(
        """
        UPDATE player_values
        SET lens_market = COALESCE(lens_market, 0) + CASE
            WHEN player_id = 'wr2' THEN 12
            WHEN player_id = 'vet1' THEN -8
            ELSE 0
        END
        WHERE league_id = 'league_x'
        """
    )

    assert client.post("/snapshots/trigger").status_code == 200

    response = client.get("/dashboard/league/league_x?roster_id=1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["league_id"] == "league_x"
    assert "user_roster_id" in payload
    assert payload["direction_read"] in {"Clear", "Leaning", "Hybrid", "Tentative", "--"}
    assert isinstance(payload["direction_alternates"], list)
    assert isinstance(payload["exploit_windows"], list)
    assert payload["exploit_windows"]
    assert isinstance(payload["risers"], list)
    assert isinstance(payload["fallers"], list)


def test_dashboard_league_returns_competitive_landscape(phase3_seed_data):
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(phase3_seed_data)
    app.dependency_overrides[get_write_db_conn] = _override_conn(phase3_seed_data)
    client = TestClient(app)

    assert client.post("/intelligence/compute/league_x").status_code == 200

    response = client.get("/dashboard/league/league_x?roster_id=1")
    assert response.status_code == 200
    landscape = response.json()["competitive_landscape"]

    assert landscape is not None
    assert {item["key"] for item in landscape["metric_summaries"]} == {
        "win_now",
        "future_value",
        "title_window",
    }
    assert landscape["win_now_rankings"]
    assert landscape["future_value_rankings"]
    assert landscape["title_window_rankings"]
    assert landscape["matchup_predictions"]
    assert landscape["matchup_predictions"][0]["verdict"] in {
        "favored",
        "toss_up",
        "underdog",
    }


def test_title_window_rankings_reward_sustainable_title_clearance(phase3_seed_data):
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(phase3_seed_data)
    app.dependency_overrides[get_write_db_conn] = _override_conn(phase3_seed_data)
    client = TestClient(app)

    assert client.post("/intelligence/compute/league_x").status_code == 200
    phase3_seed_data.execute(
        """
        UPDATE team_scorecards
        SET win_now = CASE WHEN roster_id = 1 THEN 0.95 ELSE 0.70 END,
            future_value = CASE WHEN roster_id = 1 THEN 0.10 ELSE 1.00 END,
            pick_capital = CASE WHEN roster_id = 1 THEN 0.10 ELSE 1.00 END,
            age_risk = CASE WHEN roster_id = 1 THEN 0.85 ELSE 0.10 END,
            fragility = CASE WHEN roster_id = 1 THEN 0.85 ELSE 0.10 END
        WHERE league_id = 'league_x'
        """
    )
    phase3_seed_data.execute(
        """
        UPDATE lineup_scores
        SET total_lineup_score = 10.0,
            overall_title_target = 8.0,
            overall_elite_target = 9.0,
            title_window_composite = 0.50
        WHERE league_id = 'league_x'
        """
    )

    rows = _league_competition_rows(phase3_seed_data, "league_x")
    by_roster = {int(row["roster_id"]): row for row in rows}

    assert by_roster[1]["win_now"] > by_roster[2]["win_now"]
    assert by_roster[2]["title_window"] > by_roster[1]["title_window"]


def test_dashboard_league_accepts_roster_override(phase3_seed_data):
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(phase3_seed_data)
    app.dependency_overrides[get_write_db_conn] = _override_conn(phase3_seed_data)
    client = TestClient(app)

    assert client.post("/intelligence/compute/league_x").status_code == 200

    response = client.get("/dashboard/league/league_x?roster_id=2")
    assert response.status_code == 200
    payload = response.json()
    assert payload["user_roster_id"] == 2
    assert payload["user_roster_name"] == "Roster 2"
    assert payload["user_owner_id"] == "user_b"


def test_dashboard_league_rosters_returns_selector_options(phase3_seed_data):
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(phase3_seed_data)
    app.dependency_overrides[get_write_db_conn] = _override_conn(phase3_seed_data)
    client = TestClient(app)

    response = client.get("/dashboard/league/league_x/rosters")
    assert response.status_code == 200
    payload = response.json()
    assert [row["roster_id"] for row in payload] == [1, 2]
    assert payload[0]["owner_id"] == "user_a"
    assert payload[1]["owner_id"] == "user_b"


def test_dashboard_player_rankings_include_inline_ownership(phase2_seed_data):
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(phase2_seed_data)
    app.dependency_overrides[get_write_db_conn] = _override_conn(phase2_seed_data)
    client = TestClient(app)

    assert client.post("/intelligence/compute/league_x").status_code == 200

    response = client.get("/dashboard/league/league_x/player-rankings?roster_id=1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["league_id"] == "league_x"
    assert payload["rankings"]
    first = payload["rankings"][0]
    assert first["rank"] == 1
    assert first["owner_name"]
    assert "roster_id" in first
    assert "is_user_roster" in first
    assert "position_rank" in first


def test_direction_read_marks_close_boundary_as_hybrid():
    alternates = [
        {"label": "retool", "score": 0.605, "gap": 0.004},
        {"label": "elite_value_accumulation", "score": 0.595, "gap": 0.013},
    ]

    result = _direction_read(0.288, alternates)

    assert result == "Hybrid"
    assert _direction_note("productive_struggle", result, alternates) == (
        "Hybrid read: this roster sits between Productive Struggle, Retool, "
        "and Elite Value Accumulation."
    )


def test_direction_read_keeps_diffuse_low_signal_tentative():
    alternates = [
        {"label": "fringe_playoff", "score": 0.41, "gap": 0.07},
        {"label": "true_contender", "score": 0.38, "gap": 0.10},
    ]

    result = _direction_read(0.22, alternates)

    assert result == "Tentative"


def test_exploit_windows_skip_unknown_position_chase_and_generic_windows_are_not_high(
    phase3_seed_data,
):
    phase3_seed_data.execute("DELETE FROM players")
    phase3_seed_data.execute(
        """
        INSERT INTO transactions (
            transaction_id, league_id, type, status, created_at,
            roster_ids, adds, drops, draft_picks, week
        )
        VALUES
            (
                'trade_3',
                'league_x',
                'trade',
                'complete',
                CURRENT_TIMESTAMP,
                '[1,2]',
                '{"bench_a":2}',
                '{}',
                '[{"season":"2026","round":2,"roster_id":1,"owner_id":2,"previous_owner_id":1},{"season":"2027","round":1,"roster_id":1,"owner_id":2,"previous_owner_id":1},{"season":"2027","round":2,"roster_id":1,"owner_id":2,"previous_owner_id":1}]',
                7
            )
        """
    )

    windows = _build_exploit_windows(phase3_seed_data, "league_x", 1)
    assert len(windows) == 1
    window = windows[0]
    assert window.roster_id == 2
    assert {trigger.type for trigger in window.triggers} == {
        "recent_activity",
        "pick_activity",
    }
    assert not window.is_high_opportunity


def test_exploit_windows_ignore_trades_outside_recent_window(phase3_seed_data):
    phase3_seed_data.execute(
        """
        UPDATE transactions
        SET created_at = ?
        WHERE league_id = 'league_x'
        """,
        [datetime.now() - timedelta(days=30)],
    )

    windows = _build_exploit_windows(phase3_seed_data, "league_x", 1)
    assert windows == []


def test_dashboard_risers_and_fallers_require_tradeable_rosters_in_last_90_days(
    phase3_seed_data,
):
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(phase3_seed_data)
    app.dependency_overrides[get_write_db_conn] = _override_conn(phase3_seed_data)
    client = TestClient(app)

    assert client.post("/intelligence/compute/league_x").status_code == 200
    assert client.post("/snapshots/trigger").status_code == 200

    phase3_seed_data.execute(
        """
        UPDATE player_values
        SET lens_market = COALESCE(lens_market, 0) + CASE
            WHEN player_id = 'wr2' THEN 12
            WHEN player_id = 'vet1' THEN -8
            ELSE 0
        END
        WHERE league_id = 'league_x'
        """
    )
    phase3_seed_data.execute(
        """
        UPDATE transactions
        SET created_at = ?
        WHERE league_id = 'league_x'
        """,
        [datetime.now() - timedelta(days=100)],
    )

    assert client.post("/snapshots/trigger").status_code == 200

    response = client.get("/dashboard/league/league_x")
    assert response.status_code == 200
    payload = response.json()
    assert payload["exploit_windows"] == []
    assert payload["risers"] == []
    assert payload["fallers"] == []


def test_dashboard_uses_configured_owner_display_name_for_personalized_view(
    phase3_seed_data, monkeypatch
):
    phase3_seed_data.execute(
        """
        UPDATE rosters
        SET owner_display_name = CASE
            WHEN roster_id = 1 THEN 'league-mate'
            WHEN roster_id = 2 THEN 'jakye'
            ELSE owner_display_name
        END
        WHERE league_id = 'league_x'
        """
    )

    monkeypatch.setenv("FANTASY_PORTFOLIO_OWNER_DISPLAY_NAME", "jakye")
    get_settings.cache_clear()
    try:
        app = create_app()
        app.dependency_overrides[get_read_db_conn] = _override_conn(phase3_seed_data)
        app.dependency_overrides[get_write_db_conn] = _override_conn(phase3_seed_data)
        client = TestClient(app)

        response = client.get("/dashboard/league/league_x")
        assert response.status_code == 200
        payload = response.json()
        assert {window["roster_id"] for window in payload["exploit_windows"]} == {1}
    finally:
        get_settings.cache_clear()
