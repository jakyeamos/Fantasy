from fastapi.testclient import TestClient

from fantasy.main import create_app
from fantasy.routers.deps import get_read_db_conn, get_write_db_conn


def _override_conn(conn):
    def _getter():
        yield conn

    return _getter


def test_calendar_context_is_read_only(db):
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(db)
    app.dependency_overrides[get_write_db_conn] = _override_conn(db)
    client = TestClient(app)

    response = client.get("/context/league_x/calendar")
    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {"active_state", "detected_at"}


def test_calendar_override_routes_are_unavailable(db):
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(db)
    app.dependency_overrides[get_write_db_conn] = _override_conn(db)
    client = TestClient(app)

    assert client.post(
        "/context/league_x/calendar/override",
        json={"state": "startup"},
    ).status_code == 404
    assert client.delete("/context/league_x/calendar/override").status_code == 404
