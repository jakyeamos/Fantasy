from __future__ import annotations

from fastapi.testclient import TestClient

from fantasy.main import create_app
from fantasy.picks.pick_engine import PickEngine
from fantasy.routers.deps import get_read_db_conn, get_write_db_conn
from fantasy.trade.models import TradeAsset
from fantasy.trade.trade_repo import TradeRepo


def _override_conn(conn):
    def _getter():
        yield conn

    return _getter


def _seed_pick_data(conn) -> None:
    conn.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions,
            settings_blob, superflex, tep, ppr
        )
        VALUES (
            'league_x',
            'League X',
            '2026',
            '{"rec":1.0}',
            '["QB","RB","WR","TE","SUPER_FLEX"]',
            '{"draft_rounds":2}',
            TRUE,
            FALSE,
            1.0
        )
        """
    )
    conn.execute(
        """
        INSERT INTO rosters (
            id, league_id, roster_id, owner_id, owner_display_name, starters, players, reserve, taxi
        )
        VALUES
            (1, 'league_x', 1, 'owner_a', 'Alpha', '[]', '[]', '[]', '[]'),
            (2, 'league_x', 2, 'owner_b', 'Beta', '[]', '[]', '[]', '[]')
        """
    )
    conn.execute(
        """
        INSERT INTO standings (id, league_id, roster_id, wins, losses, ties, fpts, fpts_against)
        VALUES
            (1, 'league_x', 1, 2, 10, 0, 1000, 1300),
            (2, 'league_x', 2, 10, 2, 0, 1300, 1000)
        """
    )
    conn.execute(
        """
        INSERT INTO team_directions (
            id, league_id, roster_id, primary_label, confidence, reasoning,
            alternates_json, delta_json, approved_moves, discouraged_moves
        )
        VALUES
            (1, 'league_x', 1, 'hard_rebuild', 0.9, 'seeded', '[]', '{}', '[]', '[]'),
            (2, 'league_x', 2, 'true_contender', 0.9, 'seeded', '[]', '{}', '[]', '[]')
        """
    )
    conn.execute(
        """
        INSERT INTO traded_picks (id, league_id, season, round, roster_id, owner_id, previous_owner_id)
        VALUES (1, 'league_x', '2026', 1, 2, '1', '2')
        """
    )


def test_get_league_picks_empty(db):
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(db)
    app.dependency_overrides[get_write_db_conn] = _override_conn(db)
    client = TestClient(app)

    response = client.get("/picks/league_x")
    assert response.status_code == 200
    assert response.json() == []


def test_get_league_picks_batch(db):
    _seed_pick_data(db)
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(db)
    app.dependency_overrides[get_write_db_conn] = _override_conn(db)
    client = TestClient(app)

    response = client.get("/picks/league_x")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 12
    assert {"timing_label", "timing_reasoning", "demand_adjusted_value"} <= set(payload[0])


def test_get_draft_order_rule_returns_null_when_unconfigured(db):
    _seed_pick_data(db)
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(db)
    app.dependency_overrides[get_write_db_conn] = _override_conn(db)
    client = TestClient(app)

    response = client.get("/picks/league_x/draft-order-rule")

    assert response.status_code == 200
    assert response.json() is None


def test_put_and_get_draft_order_rule_roundtrip(db):
    _seed_pick_data(db)
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(db)
    app.dependency_overrides[get_write_db_conn] = _override_conn(db)
    client = TestClient(app)

    payload = {
        "non_playoff_basis": "inverse_standings",
        "playoff_ordering": "by_finish",
        "tiebreaker": "points_against",
    }

    put_response = client.put("/picks/league_x/draft-order-rule", json=payload)
    get_response = client.get("/picks/league_x/draft-order-rule")

    assert put_response.status_code == 200
    assert put_response.json() == {"league_id": "league_x", "rule": payload}
    assert get_response.status_code == 200
    assert get_response.json() == {"league_id": "league_x", "rule": payload}


def test_picks_blocked_when_no_rule(db):
    _seed_pick_data(db)
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(db)
    app.dependency_overrides[get_write_db_conn] = _override_conn(db)
    client = TestClient(app)

    response = client.get("/picks/league_x")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 12
    assert all(item["rule_citation"] is None for item in payload)
    assert all(item["expected_draft_slot"] == 1.0 for item in payload)
    assert all(item["league_adjusted_value"] == 0.0 for item in payload)


def test_picks_configured_after_rule_save(db):
    _seed_pick_data(db)
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(db)
    app.dependency_overrides[get_write_db_conn] = _override_conn(db)
    client = TestClient(app)

    client.put(
        "/picks/league_x/draft-order-rule",
        json={
            "non_playoff_basis": "inverse_standings",
            "playoff_ordering": "by_finish",
            "tiebreaker": "points_against",
        },
    )

    response = client.get("/picks/league_x")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 12
    assert all(
        item["rule_citation"] == "Using: Inverse standings · Playoff teams by finish"
        for item in payload
    )
    assert any(item["league_adjusted_value"] > 0.0 for item in payload)


def test_picks_max_pf_configured_returns_citation(db):
    _seed_pick_data(db)
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(db)
    app.dependency_overrides[get_write_db_conn] = _override_conn(db)
    client = TestClient(app)

    client.put(
        "/picks/league_x/draft-order-rule",
        json={
            "non_playoff_basis": "max_points_for",
            "playoff_ordering": "by_points_for",
            "tiebreaker": "commissioner",
        },
    )

    response = client.get("/picks/league_x")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 12
    assert all(
        item["rule_citation"] == "Using: Max points for · Playoff teams by points for"
        for item in payload
    )


def test_get_league_picks_batch_filters_by_current_owner(db):
    _seed_pick_data(db)
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(db)
    app.dependency_overrides[get_write_db_conn] = _override_conn(db)
    client = TestClient(app)

    response = client.get("/picks/league_x?current_owner_roster_id=1")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 7
    assert any(
        item["pick"]["pick_owner_roster_id"] == 2
        and item["pick"]["pick_year"] == 2026
        and item["pick"]["pick_round"] == 1
        for item in payload
    )


def test_get_single_pick_value(db):
    _seed_pick_data(db)
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(db)
    app.dependency_overrides[get_write_db_conn] = _override_conn(db)
    client = TestClient(app)

    response = client.get("/picks/league_x/1/2026/1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["pick"]["pick_owner_roster_id"] == 1
    assert payload["pick"]["pick_year"] == 2026


def test_get_single_pick_not_found(db):
    _seed_pick_data(db)
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(db)
    app.dependency_overrides[get_write_db_conn] = _override_conn(db)
    client = TestClient(app)

    response = client.get("/picks/league_x/9/2026/1")
    assert response.status_code == 404


def test_recompute_picks(db):
    _seed_pick_data(db)
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(db)
    app.dependency_overrides[get_write_db_conn] = _override_conn(db)
    client = TestClient(app)

    response = client.post("/picks/league_x/recompute")
    assert response.status_code == 200
    assert response.json() == {"league_id": "league_x", "recomputed": 12}
    row = db.execute("SELECT COUNT(*) FROM pick_values WHERE league_id = 'league_x'").fetchone()
    assert row == (12,)


def test_trade_repo_uses_dynamic_value(db):
    _seed_pick_data(db)
    repo = TradeRepo(db)
    pick = TradeAsset(asset_type="pick", pick_owner_roster_id=1, pick_year=2026, pick_round=1)
    direct = PickEngine(db).compute(pick, "league_x", target_manager_id=2)
    via_repo = repo.get_pick_value(pick, "league_x", target_roster_id=2)
    assert via_repo.demand_adjusted_value == direct.demand_adjusted_value
