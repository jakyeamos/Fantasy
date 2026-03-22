from fastapi.testclient import TestClient

from fantasy.main import create_app
from fantasy.routers.deps import get_read_db_conn, get_write_db_conn


def _override_conn(conn):
    def _getter():
        yield conn

    return _getter


def _request(include_reroutes: bool = False, include_package: bool = False) -> dict:
    return {
        "league_id": "league_x",
        "user_roster_id": 1,
        "counterparty_roster_id": 2,
        "user_sends": [{"asset_type": "player", "player_id": "wr1"}],
        "user_receives": [{"asset_type": "player", "player_id": "qb2"}],
        "third_party_trades": [],
        "include_reroutes": include_reroutes,
        "include_package": include_package,
    }


def test_evaluate_endpoint(trade_seed_data):
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(trade_seed_data)
    app.dependency_overrides[get_write_db_conn] = _override_conn(trade_seed_data)
    client = TestClient(app)

    response = client.post("/trade/evaluate", json=_request())
    assert response.status_code == 200
    assert "market_fairness" in response.json()


def test_evaluate_with_reroutes_and_package(trade_seed_data):
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(trade_seed_data)
    app.dependency_overrides[get_write_db_conn] = _override_conn(trade_seed_data)
    client = TestClient(app)

    response = client.post(
        "/trade/evaluate",
        json=_request(include_reroutes=True, include_package=True),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["reroutes"] is not None
    assert payload["package"] is not None


def test_player_search_endpoint(trade_seed_data):
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(trade_seed_data)
    app.dependency_overrides[get_write_db_conn] = _override_conn(trade_seed_data)
    client = TestClient(app)

    response = client.get("/trade/players/search", params={"league_id": "league_x", "q": "QB"})
    assert response.status_code == 200
    assert response.json()


def test_pick_search_endpoint(trade_seed_data):
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(trade_seed_data)
    app.dependency_overrides[get_write_db_conn] = _override_conn(trade_seed_data)
    client = TestClient(app)

    response = client.get("/trade/picks/search", params={"league_id": "league_x"})
    assert response.status_code == 200
    assert response.json()
