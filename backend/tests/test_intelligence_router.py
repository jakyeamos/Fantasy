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
