from __future__ import annotations

from fastapi.testclient import TestClient

from fantasy.main import create_app
from fantasy.routers.deps import get_read_db_conn, get_write_db_conn


def _override_conn(conn):
    def _getter():
        yield conn

    return _getter


def _seed_league(
    conn,
    *,
    settings_blob: str = '{"type":2,"league_average_match":1,"best_ball":0,"salary_cap":0}',
) -> None:
    conn.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions,
            settings_blob, superflex, tep, ppr
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            "league_x",
            "League X",
            "2026",
            '{"rec":0.5,"bonus_rec_te":0.5}',
            '["QB","RB","WR","TE","SUPER_FLEX","BN"]',
            settings_blob,
            True,
            True,
            0.5,
        ],
    )


def test_get_trust_scan_returns_detected_rules(db) -> None:
    _seed_league(db)
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(db)
    app.dependency_overrides[get_write_db_conn] = _override_conn(db)
    client = TestClient(app)

    response = client.get("/trust/league_x/scan")

    assert response.status_code == 200
    payload = response.json()
    assert payload["league_id"] == "league_x"
    assert payload["needs_acknowledgment"] is True
    assert payload["league_unsupported"] is False
    assert any(entry["rule"] == "median_wins" for entry in payload["entries"])


def test_acknowledge_round_trip_persists_state(db) -> None:
    _seed_league(db)
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(db)
    app.dependency_overrides[get_write_db_conn] = _override_conn(db)
    client = TestClient(app)

    post_response = client.post("/trust/league_x/acknowledge")
    get_response = client.get("/trust/league_x/acknowledged")

    assert post_response.status_code == 200
    assert post_response.json()["acknowledgment"]["acknowledged_rules"] == ["median_wins"]
    assert get_response.status_code == 200
    assert get_response.json()["acknowledged"] is True
    assert get_response.json()["acknowledgment"]["acknowledged_rules"] == ["median_wins"]


def test_acknowledgment_is_cleared_when_rule_set_changes(db) -> None:
    _seed_league(db)
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(db)
    app.dependency_overrides[get_write_db_conn] = _override_conn(db)
    client = TestClient(app)

    assert client.post("/trust/league_x/acknowledge").status_code == 200

    db.execute(
        """
        UPDATE leagues
        SET settings_blob = '{"type":2,"league_average_match":0,"best_ball":1,"salary_cap":0}'
        WHERE league_id = 'league_x'
        """
    )

    response = client.get("/trust/league_x/acknowledged")

    assert response.status_code == 200
    assert response.json() == {
        "league_id": "league_x",
        "acknowledged": False,
        "acknowledgment": None,
    }
    assert (
        db.execute(
            "SELECT COUNT(*) FROM league_format_acknowledgments WHERE league_id = 'league_x'"
        ).fetchone()[0]
        == 0
    )
