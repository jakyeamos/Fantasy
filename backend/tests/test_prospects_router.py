from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from fantasy.main import create_app
from fantasy.routers.deps import get_write_db_conn


def _override_conn(conn):
    def _getter():
        yield conn

    return _getter


def test_prospects_router_returns_outputs_and_comps(db):
    db.execute(
        """
        INSERT INTO prospect_model_outputs (
            league_id, draft_season, player_id, player_name, position,
            archetype_label, hit_rate_bucket, tier, predicted_tier, predicted_bucket,
            risk_band, overvalue_flag_direction, overvalue_magnitude, low_confidence,
            comps_json, computed_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            "league_x",
            2026,
            "rookie_1",
            "Rookie One",
            "WR",
            "Field Stretcher",
            "High hit rate",
            1,
            1,
            "hit",
            "Low",
            "undervalued",
            3,
            False,
            json.dumps(
                [
                    {
                        "player_id": "hist_1",
                        "player_name": "Comp A",
                        "role": "ceiling",
                        "outcome_bucket": "hit",
                        "match_reason": "similar draft capital profile",
                    }
                ]
            ),
            datetime.now(timezone.utc),
        ],
    )
    db.execute(
        """
        INSERT INTO prospect_sub_flags (id, league_id, player_id, signal_name, direction, magnitude_str)
        VALUES (1, 'league_x', 'rookie_1', 'Draft Capital', 'positive', 'better than cohort median')
        """
    )

    app = create_app()
    app.dependency_overrides[get_write_db_conn] = _override_conn(db)
    client = TestClient(app)

    outputs_response = client.get("/prospects/model-outputs/league_x")
    comps_response = client.get("/prospects/comps/rookie_1")

    assert outputs_response.status_code == 200
    assert outputs_response.json()[0]["player_id"] == "rookie_1"
    assert outputs_response.json()[0]["sub_flags"][0]["signal_name"] == "Draft Capital"
    assert comps_response.status_code == 200
    assert comps_response.json()[0]["role"] == "ceiling"


def test_prospects_router_refreshes_draft_capital(monkeypatch, db):
    def _fake_refresh(conn, *, draft_year: int):
        assert draft_year == 2026
        return {
            "draft_year": draft_year,
            "source_rows": 32,
            "matched_rows": 8,
            "updated_rows": 2,
            "unmatched_rows": 24,
            "rebuilt_boards": 1,
        }

    monkeypatch.setattr(
        "fantasy.routers.prospects.refresh_actual_draft_capital",
        _fake_refresh,
    )
    app = create_app()
    app.dependency_overrides[get_write_db_conn] = _override_conn(db)
    client = TestClient(app)

    response = client.post("/prospects/draft-capital/refresh?draft_year=2026")

    assert response.status_code == 200
    assert response.json()["updated_rows"] == 2
