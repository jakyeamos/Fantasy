from __future__ import annotations

import duckdb
from fastapi.testclient import TestClient

from fantasy.main import create_app
from fantasy.routers.deps import get_read_db_conn


def _override_conn(conn):
    def _getter():
        yield conn

    return _getter


def test_process_health_does_not_require_database():
    client = TestClient(create_app())

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "fantasy-backend"}


def test_process_readiness_reports_required_runtime_tables(db):
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(db)
    client = TestClient(app)

    response = client.get("/readyz")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "service": "fantasy-backend",
        "database": "ok",
        "required_tables": ["ingest_runs", "leagues", "players", "rosters"],
    }


def test_process_readiness_rejects_incomplete_database():
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE leagues (league_id VARCHAR)")
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(conn)
    client = TestClient(app)

    response = client.get("/readyz")

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "status": "not_ready",
            "reason": "required_tables_missing",
            "missing_tables": ["ingest_runs", "players", "rosters"],
        }
    }
    conn.close()
