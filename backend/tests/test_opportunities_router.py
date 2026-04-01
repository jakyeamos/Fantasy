from fastapi.testclient import TestClient

from fantasy.main import create_app
from fantasy.routers.deps import get_read_db_conn, get_write_db_conn
from fantasy.trends.constants import COMPONENT_COLS
from fantasy.trends.trend_repo import TrendRepo


def _override_conn(conn):
    def _getter():
        yield conn

    return _getter


def _components(score: float) -> dict[str, float]:
    values = {column: score for column in COMPONENT_COLS}
    values["comp_fragility"] = max(0.0, min(1.0, 1.0 - score))
    return values


def test_opportunities_route_returns_empty_feed(db):
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(db)
    app.dependency_overrides[get_write_db_conn] = _override_conn(db)
    client = TestClient(app)

    response = client.get("/opportunities")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert payload["total"] == 0
    assert payload["computed_at"]


def test_opportunities_route_returns_items(db):
    db.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions, settings_blob, superflex, tep, ppr
        )
        VALUES ('league_x', 'League X', '2025', '{}', '[]', '{}', FALSE, FALSE, 0.5)
        """
    )
    db.execute(
        """
        INSERT INTO rosters (
            id, league_id, roster_id, owner_id, owner_display_name, starters, players, reserve, taxi
        )
        VALUES (1, 'league_x', 1, 'user_self', 'user_self', '[]', '[]', '[]', '[]')
        """
    )
    db.execute(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES ('player_1', 'Player One', 'WR', 'X', 24, '{}')
        """
    )
    db.execute(
        """
        INSERT INTO player_adp_baseline (player_id, player_name, position, adp, adp_source)
        VALUES ('player_1', 'Player One', 'WR', 82.0, 'test')
        """
    )
    repo = TrendRepo(db)
    repo.write_trend_row(
        player_id="player_1",
        season=2023,
        trend_label=None,
        confidence=None,
        delta_magnitude=0.0,
        adp_delta=None,
        components=_components(0.42),
        startup_adp=110.0,
        backfilled=False,
    )
    repo.write_trend_row(
        player_id="player_1",
        season=2024,
        trend_label=None,
        confidence=None,
        delta_magnitude=0.0,
        adp_delta=None,
        components=_components(0.88),
        startup_adp=82.0,
        backfilled=False,
    )

    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(db)
    app.dependency_overrides[get_write_db_conn] = _override_conn(db)
    client = TestClient(app)

    response = client.get("/opportunities")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["player_id"] == "player_1"
