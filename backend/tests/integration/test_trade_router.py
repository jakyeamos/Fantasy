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


def test_player_search_blank_query_returns_scoped_roster_inventory(trade_seed_data):
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(trade_seed_data)
    app.dependency_overrides[get_write_db_conn] = _override_conn(trade_seed_data)
    client = TestClient(app)

    response = client.get(
        "/trade/players/search",
        params={"league_id": "league_x", "roster_id": 1, "q": ""},
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 6
    assert payload[0]["roster_id"] == 1
    assert {item["full_name"] for item in payload} >= {"QB One", "RB One", "WR One"}


def test_player_search_blank_query_returns_selected_counterparty_roster(trade_seed_data):
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(trade_seed_data)
    app.dependency_overrides[get_write_db_conn] = _override_conn(trade_seed_data)
    client = TestClient(app)

    response = client.get(
        "/trade/players/search",
        params={"league_id": "league_x", "roster_id": 2, "q": ""},
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 6
    assert {item["roster_id"] for item in payload} == {2}
    assert {item["full_name"] for item in payload} >= {"QB Two", "RB Two", "WR Two"}
    assert "QB One" not in {item["full_name"] for item in payload}


def test_selected_counterparty_roster_player_can_be_evaluated(trade_seed_data):
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(trade_seed_data)
    app.dependency_overrides[get_write_db_conn] = _override_conn(trade_seed_data)
    client = TestClient(app)

    search_response = client.get(
        "/trade/players/search",
        params={"league_id": "league_x", "roster_id": 2, "q": ""},
    )
    assert search_response.status_code == 200
    counterparty_qb = next(
        item for item in search_response.json() if item["player_id"] == "qb2"
    )

    request = _request()
    request["user_receives"] = [
        {"asset_type": "player", "player_id": counterparty_qb["player_id"]}
    ]
    response = client.post("/trade/evaluate", json=request)

    assert response.status_code == 200
    payload = response.json()
    assert payload["market_fairness"]["confidence"] in {"HIGH", "MEDIUM", "LOW"}
    assert payload["strategic_distinction"]["headline"]


def test_player_search_falls_back_to_roster_ids_when_player_catalog_is_missing(trade_seed_data):
    trade_seed_data.execute("DELETE FROM players")
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(trade_seed_data)
    app.dependency_overrides[get_write_db_conn] = _override_conn(trade_seed_data)
    client = TestClient(app)

    response = client.get(
        "/trade/players/search",
        params={"league_id": "league_x", "roster_id": 1, "q": ""},
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 6
    assert {item["player_id"] for item in payload} >= {"qb1", "rb1", "wr1"}
    assert {item["full_name"] for item in payload} >= {"qb1", "rb1", "wr1"}


def test_pick_search_endpoint(trade_seed_data):
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(trade_seed_data)
    app.dependency_overrides[get_write_db_conn] = _override_conn(trade_seed_data)
    client = TestClient(app)

    response = client.get("/trade/picks/search", params={"league_id": "league_x"})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 18
    assert any(
        item["current_owner_id"] == 1
        and item["original_owner_id"] == 1
        and item["pick_year"] == 2027
        and item["round"] == 3
        for item in payload
    )


def test_pick_search_endpoint_returns_full_scoped_pick_inventory(trade_seed_data):
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(trade_seed_data)
    app.dependency_overrides[get_write_db_conn] = _override_conn(trade_seed_data)
    client = TestClient(app)

    response = client.get(
        "/trade/picks/search",
        params={"league_id": "league_x", "roster_id": 1},
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 11
    assert any(
        item["current_owner_id"] == 1
        and item["original_owner_id"] == 2
        and item["pick_year"] == 2025
        and item["round"] == 1
        for item in payload
    )
    assert any(
        item["current_owner_id"] == 1
        and item["original_owner_id"] == 1
        and item["pick_year"] == 2027
        and item["round"] == 3
        for item in payload
    )


def test_roster_list_endpoint(trade_seed_data):
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(trade_seed_data)
    app.dependency_overrides[get_write_db_conn] = _override_conn(trade_seed_data)
    client = TestClient(app)

    response = client.get("/trade/rosters", params={"league_id": "league_x"})
    assert response.status_code == 200
    assert response.json() == [
        {"roster_id": 1, "roster_name": "user_a"},
        {"roster_id": 2, "roster_name": "user_b"},
    ]


def test_multi_team_trade_returns_sidecar_scores_reroutes_and_package(trade_seed_data):
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(trade_seed_data)
    app.dependency_overrides[get_write_db_conn] = _override_conn(trade_seed_data)
    client = TestClient(app)

    request = _request(include_reroutes=True, include_package=True)
    request["third_party_trades"] = [
        {
            "roster_id": 3,
            "sends": [{"asset_type": "player", "player_id": "vet1"}],
            "receives": [{"asset_type": "pick", "pick_year": 2026, "pick_round": 2}],
        }
    ]

    response = client.post("/trade/evaluate", json=request)
    assert response.status_code == 200
    payload = response.json()
    assert payload["reroutes"] is not None
    assert payload["package"] is not None
    assert payload["package"]["participant_offers"] is not None
    assert {offer["roster_id"] for offer in payload["package"]["participant_offers"]} == {1, 2, 3}
    assert payload["third_party_evaluations"][0]["roster_id"] == 3
    assert "scored third-party leg" in payload["strategic_distinction"]["explanation"]
