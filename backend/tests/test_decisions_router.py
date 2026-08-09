from __future__ import annotations

from fastapi.testclient import TestClient

from fantasy.main import create_app
from fantasy.routers.deps import get_read_db_conn, get_write_db_conn


def test_decisions_endpoint_returns_canonical_empty_read_model(db) -> None:
    app = create_app()

    def override():
        yield db

    app.dependency_overrides[get_read_db_conn] = override
    app.dependency_overrides[get_write_db_conn] = override

    response = TestClient(app).get("/v2/decisions")

    assert response.status_code == 200
    assert response.json()["cards"] == []
    assert response.json()["total"] == 0
