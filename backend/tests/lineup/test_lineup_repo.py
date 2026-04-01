from __future__ import annotations

from fantasy.lineup.lineup_repo import LineupRepo
from fantasy.lineup.models import LeagueTaxiConfig


def test_taxi_config_manual_exceptions_round_trip(db):
    repo = LineupRepo(db)
    saved = repo.save_taxi_config(
        "league_repo",
        LeagueTaxiConfig(
            taxi_slots=3,
            taxi_years_eligible=2,
            years_pro_cutoff=2,
            manual_exceptions=["player_abc", "player_xyz"],
        ),
    )

    assert saved.manual_exceptions == ["player_abc", "player_xyz"]

    loaded = repo.get_taxi_config("league_repo")

    assert loaded is not None
    assert loaded.manual_exceptions == ["player_abc", "player_xyz"]


def test_taxi_config_empty_manual_exceptions_round_trip(db):
    repo = LineupRepo(db)
    repo.save_taxi_config(
        "league_repo_empty",
        LeagueTaxiConfig(
            taxi_slots=2,
            taxi_years_eligible=3,
            years_pro_cutoff=2,
            manual_exceptions=[],
        ),
    )

    loaded = repo.get_taxi_config("league_repo_empty")

    assert loaded is not None
    assert loaded.manual_exceptions == []


def test_taxi_config_defaults_manual_exceptions_to_empty_list():
    cfg = LeagueTaxiConfig(
        taxi_slots=2,
        taxi_years_eligible=2,
        years_pro_cutoff=2,
    )

    assert cfg.manual_exceptions == []


def test_taxi_config_legacy_schema_returns_empty_manual_exceptions(db):
    db.execute("DROP TABLE league_taxi_configs")
    db.execute(
        """
        CREATE TABLE league_taxi_configs (
            id                  INTEGER PRIMARY KEY,
            league_id           VARCHAR NOT NULL UNIQUE,
            taxi_slots          INTEGER NOT NULL,
            taxi_years_eligible INTEGER NOT NULL,
            years_pro_cutoff    INTEGER NOT NULL,
            created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    db.execute(
        """
        INSERT INTO league_taxi_configs (
            id, league_id, taxi_slots, taxi_years_eligible, years_pro_cutoff
        )
        VALUES (1, 'legacy_league', 4, 2, 2)
        """
    )

    repo = LineupRepo(db)
    loaded = repo.get_taxi_config("legacy_league")

    assert loaded is not None
    assert loaded.manual_exceptions == []
