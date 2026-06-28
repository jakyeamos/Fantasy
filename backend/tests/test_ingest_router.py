from __future__ import annotations

from fastapi.testclient import TestClient

from fantasy.edge_radar.player_metadata import PlayerMetadataRefreshSummary
from fantasy.edge_radar.team_context import TeamContextRefreshSummary
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


def test_refresh_team_context_route_runs_environment_refresh(monkeypatch, db):
    calls: list[int] = []

    class _FakeTeamContextRefreshService:
        def __init__(self, conn):
            assert conn is db

        def refresh(self, season: int):
            calls.append(season)
            return TeamContextRefreshSummary(
                season=season,
                environment_rows=32,
                upserted_rows=32,
            )

    monkeypatch.setattr(
        "fantasy.routers.ingest.TeamContextRefreshService",
        _FakeTeamContextRefreshService,
    )

    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _unexpected_read_conn
    app.dependency_overrides[get_write_db_conn] = _override_conn(db)
    client = TestClient(app)

    response = client.post("/ingest/team-context/refresh?season=2026")

    assert response.status_code == 200
    assert response.json() == {
        "season": 2026,
        "environment_rows": 32,
        "upserted_rows": 32,
    }
    assert calls == [2026]


def test_refresh_player_metadata_route_runs_dense_signal_refresh(monkeypatch, db):
    calls: list[int] = []

    class _FakePlayerMetadataRefreshService:
        def __init__(self, conn):
            assert conn is db

        def refresh(self, season: int):
            calls.append(season)
            return PlayerMetadataRefreshSummary(
                season=season,
                source_rows=240,
                updated_rows=236,
            )

    monkeypatch.setattr(
        "fantasy.routers.ingest.PlayerMetadataRefreshService",
        _FakePlayerMetadataRefreshService,
    )

    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _unexpected_read_conn
    app.dependency_overrides[get_write_db_conn] = _override_conn(db)
    client = TestClient(app)

    response = client.post("/ingest/player-metadata/refresh?season=2026")

    assert response.status_code == 200
    assert response.json() == {
        "season": 2026,
        "source_rows": 240,
        "updated_rows": 236,
    }
    assert calls == [2026]


def test_refresh_league_pipeline_runs_all_offseason_refresh_steps(monkeypatch, db):
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
    calls: list[tuple[str, object]] = []

    class _FakeSleeperClient:
        async def __aenter__(self):
            calls.append(("sleeper_client", "enter"))
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            calls.append(("sleeper_client", "exit"))

    class _FakeIngestService:
        def __init__(self, conn, client):
            calls.append(("ingest_init", client.__class__.__name__))

        async def run(self, league_id: str, run_type: str) -> int:
            calls.append(("ingest_run", (league_id, run_type)))
            return 42

    async def _fake_refresh_adp(conn, *, num_qbs: int, num_teams: int, ppr: float):
        calls.append(("adp", (num_qbs, num_teams, ppr)))
        return {
            "source_rows": 100,
            "matched_rows": 90,
            "matched_unique_rows": 80,
            "unmatched_rows": 10,
        }

    def _fake_refresh_draft_capital(conn, *, draft_year: int):
        calls.append(("draft_capital", draft_year))
        return {
            "draft_year": draft_year,
            "source_rows": 25,
            "matched_rows": 20,
            "updated_rows": 18,
            "unmatched_rows": 5,
            "rebuilt_boards": 1,
        }

    def _fake_refresh_artifacts(conn, league_id: str):
        calls.append(("artifacts", league_id))
        return {
            "league_id": league_id,
            "roster_count": 12,
            "player_value_count": 240,
            "manager_profile_count": 12,
            "snapshot_count": 1,
        }

    monkeypatch.setattr("fantasy.routers.ingest.SleeperClient", _FakeSleeperClient)
    monkeypatch.setattr("fantasy.routers.ingest.IngestService", _FakeIngestService)
    monkeypatch.setattr("fantasy.routers.ingest.refresh_adp_baseline_from_fantasycalc", _fake_refresh_adp)
    monkeypatch.setattr("fantasy.routers.ingest.refresh_actual_draft_capital", _fake_refresh_draft_capital)
    monkeypatch.setattr("fantasy.routers.ingest.refresh_league_artifacts", _fake_refresh_artifacts)

    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _unexpected_read_conn
    app.dependency_overrides[get_write_db_conn] = _override_conn(db)
    client = TestClient(app)

    response = client.post("/ingest/lg1/refresh-pipeline?run_type=incremental&draft_year=2026")

    assert response.status_code == 200
    assert response.json() == {
        "league_id": "lg1",
        "run_id": 42,
        "run_type": "incremental",
        "sleeper_status": "complete",
        "adp": {
            "source": "fantasycalc_api",
            "source_rows": 100,
            "matched_rows": 90,
            "matched_unique_rows": 80,
            "unmatched_rows": 10,
            "num_qbs": 2,
            "num_teams": 12,
            "ppr": 0.5,
        },
        "draft_capital": {
            "draft_year": 2026,
            "source_rows": 25,
            "matched_rows": 20,
            "updated_rows": 18,
            "unmatched_rows": 5,
            "rebuilt_boards": 1,
        },
        "artifacts": {
            "league_id": "lg1",
            "roster_count": 12,
            "player_value_count": 240,
            "manager_profile_count": 12,
            "snapshot_count": 1,
        },
    }
    assert calls == [
        ("sleeper_client", "enter"),
        ("ingest_init", "_FakeSleeperClient"),
        ("ingest_run", ("lg1", "incremental")),
        ("sleeper_client", "exit"),
        ("adp", (2, 12, 0.5)),
        ("draft_capital", 2026),
        ("artifacts", "lg1"),
    ]
