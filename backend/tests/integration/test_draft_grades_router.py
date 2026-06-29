import json

from fastapi.testclient import TestClient

from fantasy.main import create_app
from fantasy.routers.deps import get_read_db_conn


def _override_conn(conn):
    def _getter():
        yield conn

    return _getter


def _seed_draft_selection_rows(conn):
    conn.execute(
        """
        INSERT INTO draft_pick_selections (
            id, league_id, draft_id, roster_id, player_id, pick_slot,
            round_number, season, draft_type, position, archetype_label, ingested_at
        )
        VALUES
            (1, 'league_x', 'rookie_draft', 1, 'wr1', 1, 1, 2025, 'rookie', 'WR', 'separator', TIMESTAMP '2025-05-01 12:00:00'),
            (2, 'league_x', 'rookie_draft', 2, 'qb2', 2, 1, 2025, 'rookie', 'QB', 'pocket', TIMESTAMP '2025-05-01 12:00:00'),
            (3, 'league_x', 'startup_draft', 1, 'rb1', 1, 1, 2025, 'startup', 'RB', NULL, TIMESTAMP '2025-04-01 12:00:00')
        """
    )


def test_draft_grades_returns_rookie_and_startup_team_summaries(trade_seed_data):
    _seed_draft_selection_rows(trade_seed_data)
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(trade_seed_data)
    client = TestClient(app)

    response = client.get("/draft-grades/league_x")

    assert response.status_code == 200
    payload = response.json()
    assert {item["draft_type"] for item in payload["selections"]} == {"rookie", "startup"}
    assert payload["team_summaries"]
    assert payload["best_value"] is not None
    assert payload["biggest_reach"] is not None


def test_draft_grades_marks_at_time_available_from_prior_snapshot(trade_seed_data):
    _seed_draft_selection_rows(trade_seed_data)
    trade_seed_data.execute(
        """
        INSERT INTO league_snapshots (
            id, league_id, snapshot_at, snapshot_type, triggered_by, payload_json
        )
        VALUES (1, 'league_x', TIMESTAMP '2025-03-01 12:00:00', 'full', 'test', ?)
        """,
        [
            json.dumps(
                {
                    "state": {
                        "rosters": [
                            {
                                "roster_id": 1,
                                "player_values": [
                                    {"player_id": "rb1", "lens_market": 0.72},
                                    {"player_id": "wr1", "lens_market": 0.88},
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
    client = TestClient(app)

    response = client.get("/draft-grades/league_x")

    assert response.status_code == 200
    payload = response.json()
    rb_pick = next(item for item in payload["selections"] if item["player_id"] == "rb1")
    assert rb_pick["at_time"]["status"] == "available"
    assert rb_pick["at_time"]["value"] == 0.72


def test_draft_grades_marks_at_time_unavailable_without_snapshot(trade_seed_data):
    _seed_draft_selection_rows(trade_seed_data)
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(trade_seed_data)
    client = TestClient(app)

    response = client.get("/draft-grades/league_x")

    assert response.status_code == 200
    payload = response.json()
    assert all(item["at_time"]["status"] == "unavailable" for item in payload["selections"])
