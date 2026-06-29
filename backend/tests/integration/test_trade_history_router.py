import json

from fastapi.testclient import TestClient

from fantasy.main import create_app
from fantasy.routers.deps import get_read_db_conn, get_write_db_conn


def _override_conn(conn):
    def _getter():
        yield conn

    return _getter


def test_trade_history_parses_completed_trade_and_pick_direction(trade_seed_data):
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(trade_seed_data)
    app.dependency_overrides[get_write_db_conn] = _override_conn(trade_seed_data)
    client = TestClient(app)

    response = client.get("/trade/history/league_x")

    assert response.status_code == 200
    payload = response.json()
    trade = next(item for item in payload["trades"] if item["transaction_id"] == "prof_trade_1")
    roster_one = next(item for item in trade["participants"] if item["roster_id"] == 1)
    assert "WR One" in {asset["label"] for asset in roster_one["sends"]}
    assert "QB Two" in {asset["label"] for asset in roster_one["receives"]}
    assert "2026 Round 1" in {asset["label"] for asset in roster_one["sends"]}
    assert roster_one["current_replay"]["trade_balance"] is not None
    assert trade["current_winner_roster_id"] in {1, 2}


def test_trade_history_degrades_when_player_values_missing(trade_seed_data):
    trade_seed_data.execute("DELETE FROM player_values WHERE league_id = 'league_x'")
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(trade_seed_data)
    app.dependency_overrides[get_write_db_conn] = _override_conn(trade_seed_data)
    client = TestClient(app)

    response = client.get("/trade/history/league_x")

    assert response.status_code == 200
    payload = response.json()
    assert payload["trades"]
    assert payload["trades"][0]["participants"][0]["current_replay"] is not None
    assert payload["trades"][0]["at_time_status"] == "unavailable"


def test_trade_history_marks_at_time_available_from_prior_snapshot(trade_seed_data):
    trade_seed_data.execute(
        """
        INSERT INTO league_snapshots (
            id, league_id, snapshot_at, snapshot_type, triggered_by, payload_json
        )
        VALUES (1, 'league_x', TIMESTAMP '2024-12-15 12:00:00', 'full', 'test', ?)
        """,
        [
            json.dumps(
                {
                    "state": {
                        "rosters": [
                            {
                                "roster_id": 1,
                                "player_values": [
                                    {"player_id": "wr1", "lens_market": 0.9},
                                    {"player_id": "qb2", "lens_market": 0.4},
                                ],
                            }
                        ]
                    }
                }
            )
        ],
    )
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(trade_seed_data)
    app.dependency_overrides[get_write_db_conn] = _override_conn(trade_seed_data)
    client = TestClient(app)

    response = client.get("/trade/history/league_x")

    assert response.status_code == 200
    payload = response.json()
    trade = next(item for item in payload["trades"] if item["transaction_id"] == "prof_trade_1")
    roster_one = next(item for item in trade["participants"] if item["roster_id"] == 1)
    assert trade["at_time_status"] == "available"
    assert roster_one["at_time_status"] == "available"
