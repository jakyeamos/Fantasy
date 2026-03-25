from fastapi.testclient import TestClient

from fantasy.main import create_app
from fantasy.routers.deps import get_read_db_conn, get_write_db_conn


def _override_conn(conn):
    def _getter():
        yield conn

    return _getter


def test_scorecard_endpoint(phase2_seed_data):
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(phase2_seed_data)
    app.dependency_overrides[get_write_db_conn] = _override_conn(phase2_seed_data)
    client = TestClient(app)
    assert client.post("/intelligence/compute/league_x").status_code == 200
    response = client.get("/intelligence/scorecard/league_x/1")
    assert response.status_code == 200
    assert "win_now" in response.json()


def test_direction_endpoint(phase2_seed_data):
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(phase2_seed_data)
    app.dependency_overrides[get_write_db_conn] = _override_conn(phase2_seed_data)
    client = TestClient(app)
    client.post("/intelligence/compute/league_x")
    response = client.get("/intelligence/direction/league_x/1")
    assert response.status_code == 200
    assert "primary_label" in response.json()


def test_player_value_endpoint(phase2_seed_data):
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(phase2_seed_data)
    app.dependency_overrides[get_write_db_conn] = _override_conn(phase2_seed_data)
    client = TestClient(app)
    client.post("/intelligence/compute/league_x")
    response = client.get("/intelligence/player-value/league_x/1/wr1")
    assert response.status_code == 200
    assert "lens_market" in response.json()


def test_lineup_endpoint(phase2_seed_data):
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(phase2_seed_data)
    app.dependency_overrides[get_write_db_conn] = _override_conn(phase2_seed_data)
    client = TestClient(app)
    client.post("/intelligence/compute/league_x")
    response = client.get("/intelligence/lineup/league_x/1")
    assert response.status_code == 200
    body = response.json()
    assert "slot_scores" in body
    assert "title_window_label" in body


def test_hygiene_endpoint(phase2_seed_data):
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(phase2_seed_data)
    app.dependency_overrides[get_write_db_conn] = _override_conn(phase2_seed_data)
    client = TestClient(app)
    client.post("/intelligence/compute/league_x")
    response = client.get("/intelligence/hygiene/league_x/1")
    assert response.status_code == 200
    assert "suggestions" in response.json()


def test_taxi_config_get_put(phase2_seed_data):
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(phase2_seed_data)
    app.dependency_overrides[get_write_db_conn] = _override_conn(phase2_seed_data)
    client = TestClient(app)
    r0 = client.get("/leagues/league_x/taxi-config")
    assert r0.status_code == 200
    assert r0.json()["config"] is None

    payload = {
        "taxi_slots": 4,
        "taxi_years_eligible": 2,
        "years_pro_cutoff": 2,
    }
    r1 = client.put("/leagues/league_x/taxi-config", json=payload)
    assert r1.status_code == 200
    assert r1.json()["config"]["taxi_slots"] == 4

    r2 = client.get("/leagues/league_x/taxi-config")
    assert r2.json()["config"]["taxi_slots"] == 4

    r3 = client.get("/leagues/league_x/slot-occupancy/1")
    assert r3.status_code == 200
    assert "taxi_used" in r3.json()
