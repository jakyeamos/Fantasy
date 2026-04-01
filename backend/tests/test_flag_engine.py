from __future__ import annotations

import json

from fantasy.player_flags.flag_engine import FlagEngine
from fantasy.player_flags.flag_repo import FlagRepo


def _insert_player(db, player_id: str, *, position: str = "WR", team: str = "ATL", age: int = 26, metadata: dict | None = None) -> None:
    db.execute(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [player_id, player_id, position, team, age, json.dumps(metadata or {})],
    )


def test_injury_recovery_derives_from_ir_status(db) -> None:
    _insert_player(
        db,
        "p1",
        metadata={"injury_status": "IR"},
    )
    flags = FlagEngine(db).derive_flags_for_player("p1")
    assert "injury_recovery" in [flag.flag_type for flag in flags]


def test_depth_chart_competition_derives_from_depth_chart_order(db) -> None:
    _insert_player(
        db,
        "p2",
        metadata={"depth_chart_order": 2},
    )
    flags = FlagEngine(db).derive_flags_for_player("p2")
    assert "depth_chart_competition" in [flag.flag_type for flag in flags]


def test_age_cliff_proximity_derives_near_cliff_age(db) -> None:
    _insert_player(db, "p3", position="RB", age=28)
    flags = FlagEngine(db).derive_flags_for_player("p3")
    assert "age_cliff_proximity" in [flag.flag_type for flag in flags]


def test_team_change_derives_from_previous_team(db) -> None:
    _insert_player(
        db,
        "p4",
        team="BUF",
        metadata={"previous_team": "LAR"},
    )
    flags = FlagEngine(db).derive_flags_for_player("p4")
    assert "team_change" in [flag.flag_type for flag in flags]


def test_flag_repo_returns_active_flags(db) -> None:
    _insert_player(
        db,
        "p5",
        metadata={"injury_status": "Out"},
    )
    engine = FlagEngine(db)
    engine.derive_flags_for_player("p5")
    repo = FlagRepo(db)
    active = repo.get_active_flags("p5")
    assert active
    assert active[0].player_id == "p5"
