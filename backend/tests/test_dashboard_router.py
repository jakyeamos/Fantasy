from fastapi.testclient import TestClient

from fantasy.main import create_app
from fantasy.routers.deps import get_read_db_conn, get_write_db_conn


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
    assert league["primary_weakness"]
    assert league["top_exploit_window"] is not None


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

    response = client.get("/dashboard/league/league_x")
    assert response.status_code == 200
    payload = response.json()
    assert payload["league_id"] == "league_x"
    assert isinstance(payload["exploit_windows"], list)
    assert payload["exploit_windows"]
    assert isinstance(payload["risers"], list)
    assert isinstance(payload["fallers"], list)
