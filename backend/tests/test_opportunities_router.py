from fastapi.testclient import TestClient

from fantasy.main import create_app
from fantasy.routers.deps import get_read_db_conn, get_write_db_conn
from fantasy.trends.models import SimilarPlayer
from fantasy.trends.constants import COMPONENT_COLS
from fantasy.trends import opportunity_engine
from fantasy.trends.trend_repo import TrendRepo


class _CountingConnection:
    def __init__(self, conn):
        self._conn = conn
        self.execute_count = 0

    def execute(self, *args, **kwargs):
        self.execute_count += 1
        return self._conn.execute(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._conn, name)


def _override_conn(conn):
    def _getter():
        yield conn

    return _getter


def _components(score: float) -> dict[str, float]:
    values = {column: score for column in COMPONENT_COLS}
    values["comp_fragility"] = max(0.0, min(1.0, 1.0 - score))
    return values


def _seed_route_opportunity(
    conn,
    *,
    player_id: str,
    player_name: str,
    adp: float,
) -> None:
    conn.execute(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES (?, ?, 'WR', 'X', 24, '{}')
        """,
        [player_id, player_name],
    )
    conn.execute(
        """
        INSERT INTO player_adp_baseline (player_id, player_name, position, adp, adp_source)
        VALUES (?, ?, 'WR', ?, 'test')
        """,
        [player_id, player_name, adp],
    )
    repo = TrendRepo(conn)
    repo.write_trend_row(
        player_id=player_id,
        season=2023,
        trend_label=None,
        confidence=None,
        delta_magnitude=0.0,
        adp_delta=None,
        components=_components(0.42),
        startup_adp=adp + 35.0,
        backfilled=False,
    )
    repo.write_trend_row(
        player_id=player_id,
        season=2024,
        trend_label=None,
        confidence=None,
        delta_magnitude=0.0,
        adp_delta=None,
        components=_components(0.88),
        startup_adp=adp,
        backfilled=False,
    )


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
    assert payload["items"][0]["cta"]["destination"] == "player_rankings"
    assert payload["items"][0]["cta"]["league_id"] == "league_x"


def test_opportunities_route_uses_bounded_query_count(db):
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
    for index in range(40):
        _seed_route_opportunity(
            db,
            player_id=f"player_{index}",
            player_name=f"Player {index}",
            adp=70.0 + index,
        )

    counted_db = _CountingConnection(db)
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(counted_db)
    app.dependency_overrides[get_write_db_conn] = _override_conn(counted_db)
    client = TestClient(app)

    response = client.get("/opportunities")

    assert response.status_code == 200
    assert response.json()["total"] == 40
    assert counted_db.execute_count <= 20


def test_opportunities_route_returns_degraded_partial_feed(db, monkeypatch):
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
    _seed_route_opportunity(
        db,
        player_id="player_degraded",
        player_name="Player Degraded",
        adp=70.0,
    )

    def _raise_similarity(_player_id, _snapshots):
        raise RuntimeError("similarity unavailable")

    monkeypatch.setattr(
        opportunity_engine,
        "find_similar_players_from_snapshots",
        _raise_similarity,
    )
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(db)
    app.dependency_overrides[get_write_db_conn] = _override_conn(db)
    client = TestClient(app)

    response = client.get("/opportunities")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["status"] == "degraded"
    assert payload["degraded_reason"]


def test_opportunities_route_marks_stale_similar_player_evidence(db, monkeypatch):
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
    _seed_route_opportunity(
        db,
        player_id="player_stale",
        player_name="Player Stale",
        adp=70.0,
    )

    def _similar_players(_player_id, _snapshots):
        return [
            SimilarPlayer(
                player_id="comp_1",
                player_name="Comp One",
                similarity_score=0.89,
                archetype_label="route winner",
                context="similar role and market movement",
            )
        ]

    monkeypatch.setattr(
        opportunity_engine,
        "find_similar_players_from_snapshots",
        _similar_players,
    )
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(db)
    app.dependency_overrides[get_write_db_conn] = _override_conn(db)
    client = TestClient(app)

    response = client.get("/opportunities")

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["similar_players"]
    assert item["evidence_freshness"]["is_stale"] is True
    assert item["evidence_freshness"]["stale_domains"] == [
        "player_metadata",
        "team_context",
    ]
