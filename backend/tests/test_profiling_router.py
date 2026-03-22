from fastapi.testclient import TestClient

from fantasy.main import create_app
from fantasy.routers.deps import get_read_db_conn, get_write_db_conn


def _override_conn(conn):
    def _getter():
        yield conn

    return _getter


def test_compute_profiles_endpoint(profiling_seed_data):
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(profiling_seed_data)
    app.dependency_overrides[get_write_db_conn] = _override_conn(profiling_seed_data)
    client = TestClient(app)

    response = client.post("/profiling/leagues/league_x/managers/compute")
    assert response.status_code == 200
    assert response.json()["computed"] == 2


def test_list_managers_endpoint(profiling_seed_data):
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(profiling_seed_data)
    app.dependency_overrides[get_write_db_conn] = _override_conn(profiling_seed_data)
    client = TestClient(app)

    client.post("/profiling/leagues/league_x/managers/compute")
    response = client.get("/profiling/leagues/league_x/managers")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
    assert "exploitability_score" in payload[0]


def test_get_manager_profile_endpoint(profiling_seed_data):
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(profiling_seed_data)
    app.dependency_overrides[get_write_db_conn] = _override_conn(profiling_seed_data)
    client = TestClient(app)

    client.post("/profiling/leagues/league_x/managers/compute")
    response = client.get("/profiling/leagues/league_x/managers/1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["roster_id"] == 1
    assert payload["pitch_angles"]
