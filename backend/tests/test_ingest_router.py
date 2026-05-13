from __future__ import annotations

from fastapi.testclient import TestClient

from fantasy.main import create_app
from fantasy.routers.deps import get_read_db_conn, get_write_db_conn


def _override_conn(conn):
    def _getter():
        yield conn

    return _getter


def _unexpected_read_conn():
    raise AssertionError("ingest router should not request a read-only connection")


def test_refresh_adp_baseline_uses_league_profile(monkeypatch, db):
    db.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions, settings_blob, superflex, tep, ppr
        )
        VALUES ('lg1', 'League 1', '2026', '{}', '[]', '{}', TRUE, FALSE, 0.5)
        """
    )
    db.executemany(
        """
        INSERT INTO rosters (id, league_id, roster_id, starters, players)
        VALUES (?, 'lg1', ?, '[]', '[]')
        """,
        [[i, i] for i in range(1, 13)],
    )

    async def _fake_refresh(conn, *, num_qbs: int, num_teams: int, ppr: float):
        assert num_qbs == 2
        assert num_teams == 12
        assert ppr == 0.5
        return {
            "source_rows": 10,
            "matched_rows": 9,
            "matched_unique_rows": 8,
            "unmatched_rows": 1,
        }

    monkeypatch.setattr("fantasy.routers.ingest.refresh_adp_baseline_from_fantasycalc", _fake_refresh)

    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _unexpected_read_conn
    app.dependency_overrides[get_write_db_conn] = _override_conn(db)
    client = TestClient(app)

    response = client.post("/ingest/adp-baseline/refresh?league_id=lg1")
    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "source": "fantasycalc_api",
        "source_rows": 10,
        "matched_rows": 9,
        "matched_unique_rows": 8,
        "unmatched_rows": 1,
        "num_qbs": 2,
        "num_teams": 12,
        "ppr": 0.5,
    }
