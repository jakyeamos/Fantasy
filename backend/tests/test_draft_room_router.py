from __future__ import annotations

from fastapi.testclient import TestClient

from fantasy.main import create_app
from fantasy.routers.deps import get_read_db_conn, get_write_db_conn


def _override_conn(conn):
    def _getter():
        yield conn

    return _getter


def _unexpected_read_conn():
    raise AssertionError("draft-room should not request a read-only connection")


def _seed_rookie_route_data(conn) -> None:
    from tests.rookie.test_rookie_repo import _seed_rookie_data

    _seed_rookie_data(conn)


def test_draft_room_router_returns_result(db):
    _seed_rookie_route_data(db)
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _unexpected_read_conn
    app.dependency_overrides[get_write_db_conn] = _override_conn(db)
    client = TestClient(app)

    response = client.get("/draft-room/league_rookie/3")
    assert response.status_code == 200
    payload = response.json()
    assert payload["league_id"] == "league_rookie"
    assert payload["trade_verdict"]["label"] in {"Trade it", "Use it"}
