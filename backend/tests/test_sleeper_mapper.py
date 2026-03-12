import pytest

from fantasy.ingestion.sleeper_mapper import SleeperMapper


def test_map_league_settings(mock_league_response):
    league = SleeperMapper.map_league(mock_league_response)
    assert league.league_id == "test_league_001"
    assert league.season == "2025"
    assert league.ppr == 1.0
    assert league.superflex is True
    assert league.tep is True


def test_flag_derivation():
    league_half_ppr = SleeperMapper.map_league(
        {
            "league_id": "league_b",
            "name": "League B",
            "season": "2025",
            "scoring_settings": {"rec": 0.5, "bonus_rec_te": 0},
            "roster_positions": ["QB", "RB", "WR", "TE"],
            "settings": {},
        }
    )

    assert league_half_ppr.superflex is False
    assert league_half_ppr.tep is False
    assert league_half_ppr.ppr == 0.5


def test_map_roster(mock_roster_response):
    roster = SleeperMapper.map_roster(mock_roster_response)

    assert roster.starters == ["4017", "4663"]
    assert roster.taxi == ["8888"]
    assert roster.ir == ["5122"]
    assert "2374" in roster.bench
    assert "6945" in roster.bench


def test_map_traded_picks(mock_traded_pick_response):
    picks = SleeperMapper.map_traded_picks(mock_traded_pick_response)

    assert len(picks) == 2
    assert picks[0].season == "2025"
    assert picks[0].round == 1
    assert picks[1].previous_owner_id is None


def test_partial_response_handling():
    roster = SleeperMapper.map_roster(
        {
            "roster_id": 1,
            "owner_id": None,
            "league_id": "league_partial",
            "starters": ["100"],
            "players": ["100", "101"],
            "reserve": None,
            "taxi": None,
        }
    )
    assert roster.ir == []

    league = SleeperMapper.map_league(
        {
            "league_id": "league_partial",
            "name": "Partial",
            "season": "2025",
            "scoring_settings": {},
            "roster_positions": ["QB", "RB", "WR", "TE"],
            "settings": {},
        }
    )
    assert league.ppr == 0.0
    assert league.tep is False
    assert league.superflex is False

    with pytest.raises(Exception):
        SleeperMapper.map_league({"name": "Missing ID"})
