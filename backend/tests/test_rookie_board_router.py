from __future__ import annotations

from fastapi.testclient import TestClient

from fantasy.main import create_app
from fantasy.routers.deps import get_read_db_conn, get_write_db_conn


def _override_conn(conn):
    def _getter():
        yield conn

    return _getter


def _unexpected_read_conn():
    raise AssertionError("rookie-board should not request a read-only connection")


def _seed_rookie_route_data(conn) -> None:
    from tests.rookie.test_rookie_repo import _seed_rookie_data

    _seed_rookie_data(conn)


def test_rookie_board_router_returns_board(db):
    _seed_rookie_route_data(db)
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _unexpected_read_conn
    app.dependency_overrides[get_write_db_conn] = _override_conn(db)
    client = TestClient(app)

    response = client.get("/rookie-board/league_rookie")
    assert response.status_code == 200
    payload = response.json()
    assert payload["rookie_board"]["league_id"] == "league_rookie"
    assert isinstance(payload["rookie_board"]["tiers"], list)
    assert payload["recommendation_context"]["calendar_state"]
