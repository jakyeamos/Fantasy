from __future__ import annotations

from pathlib import Path

from fantasy.rookie_pick.models import DraftPickSelection, RookiePickProfile
from fantasy.rookie_pick.rookie_pick_repo import RookiePickRepo


def test_upsert_profile_roundtrip(db) -> None:
    repo = RookiePickRepo(db)
    profile = RookiePickProfile(
        league_id="league_x",
        roster_id=1,
        computed_at="2026-01-01T00:00:00+00:00",
        pick_premium_score=0.22,
        pick_trade_evidence=4,
        draft_selection_count=3,
        positional_tendency={"WR": 0.2},
        dominant_archetype="Deep Threat",
        archetype_pattern={"Deep Threat": 2},
        show_draft_picks_tab=True,
    )

    repo.upsert_profile(profile)
    loaded = repo.get_profile("league_x", 1)

    assert loaded is not None
    assert loaded.pick_premium_score == 0.22
    assert loaded.pick_trade_evidence == 4
    assert loaded.dominant_archetype == "Deep Threat"


def test_upsert_draft_selection_roundtrip(db) -> None:
    repo = RookiePickRepo(db)
    selection = DraftPickSelection(
        league_id="league_x",
        draft_id="draft_1",
        roster_id=1,
        player_id="player_1",
        pick_slot=5,
        round_number=1,
        season=2026,
        draft_type="startup",
        position="WR",
        archetype_label="Deep Threat",
    )

    repo.upsert_draft_selection(selection)
    loaded = repo.get_draft_selections("league_x", 1)

    assert loaded == [
        {
            "player_id": "player_1",
            "pick_slot": 5,
            "round_number": 1,
            "season": 2026,
            "draft_type": "startup",
            "position": "WR",
            "archetype_label": "Deep Threat",
        }
    ]


def test_schema_tables_exist_in_conftest() -> None:
    schema_blob = Path(__file__).resolve().parents[1].joinpath("conftest.py").read_text()
    assert "draft_pick_selections" in schema_blob
    assert "manager_rookie_pick_profiles" in schema_blob
