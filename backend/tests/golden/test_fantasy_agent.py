from datetime import datetime

from fantasy.agent_context import build_agent_context
from tests.test_agent_context import _seed_burrow_context


def _decision(db, question: str):
    result = build_agent_context(
        db,
        question=question,
        owner_display_name="jakye",
        now=datetime(2026, 8, 3, 12, 0, 0),
    )
    return result["decision_packets"][0]


def test_elite_superflex_qb_for_generic_picks_requests_details(db):
    _seed_burrow_context(db)
    db.execute(
        """
        INSERT INTO player_adp_baseline
            (player_id, player_name, position, adp, adp_source)
        VALUES ('6770', 'Joe Burrow', 'QB', 14, 'test')
        """
    )

    packet = _decision(db, "Would you trade Joe Burrow for straight picks?")

    assert packet["recommendation"]["action"] == "request_details"
    assert packet["recommendation"]["minimum_return"] == [
        "At least two first-round-equivalent assets",
        "At least one premium or plausibly early first-round asset",
        "No return made only of distant projected-mid picks",
    ]
    assert packet["evidence"]["market"]["market_value"] is None
    assert "Market value unavailable" in packet["limitations"][0]


def test_partially_specified_pick_offer_names_the_remaining_gap(db):
    _seed_burrow_context(db)

    packet = _decision(db, "Joe Burrow for a 2027 first and a 2028 first")

    assert packet["interpretation"]["status"] == "partially_specified"
    assert packet["interpretation"]["missing_details"] == ["projected pick ranges"]
    assert packet["recommendation"]["action"] == "request_details"


def test_fully_described_picks_still_require_counterparty_evaluation(db):
    _seed_burrow_context(db)

    packet = _decision(db, "Joe Burrow for a 2027 early first and 2028 mid first")

    assert packet["interpretation"]["status"] == "specified"
    assert packet["recommendation"]["action"] == "hold_pending_evaluation"


def test_unconfigured_owner_does_not_fabricate_a_decision(db, monkeypatch):
    _seed_burrow_context(db)
    monkeypatch.delenv("FANTASY_PORTFOLIO_OWNER_ID", raising=False)
    monkeypatch.delenv("FANTASY_PORTFOLIO_OWNER_DISPLAY_NAME", raising=False)

    result = build_agent_context(
        db,
        question="Would you trade Joe Burrow for picks?",
        owner_id="missing-owner",
        now=datetime(2026, 8, 3, 12, 0, 0),
    )

    assert result["decision_packets"] == []
    assert "No rosters matched" in result["gaps"][0]


def test_stale_ingest_is_exposed_as_a_decision_gap(db):
    _seed_burrow_context(db)

    result = build_agent_context(
        db,
        question="Would you trade Joe Burrow for picks?",
        owner_display_name="jakye",
        now=datetime(2026, 8, 6, 12, 0, 0),
    )

    assert result["leagues"][0]["ingest"]["status"] == "stale"
    assert result["leagues"][0]["data_health"]["semantic_status"] == "stale"
    assert "ingest is stale" in result["gaps"][0]


def test_corrupt_current_season_is_blocked_and_prior_season_is_labeled(db):
    _seed_burrow_context(db)
    db.execute(
        """
        INSERT INTO player_stats_weekly
            (player_id, player_name, position, season, week, fantasy_points,
             targets, carries, passing_yards, receiving_yards, rushing_yards)
        SELECT 'p' || player_no, 'Player ' || player_no, 'WR', 2025, week,
               player_no + week, week, player_no, 0, player_no + week, 0
        FROM range(1, 21) players(player_no)
        CROSS JOIN range(1, 7) weeks(week)
        """
    )
    db.execute(
        "INSERT INTO player_stats_weekly SELECT * REPLACE (2026 AS season) FROM player_stats_weekly WHERE season = 2025"
    )

    packet = _decision(db, "Would you trade Joe Burrow for picks?")
    health = packet["evidence"]["data_health"]

    assert health["integrity_status"] == "blocked_by_integrity_failure"
    assert health["scoring_season"] == 2025
    assert health["scoring_status"] == "fallback_valid"
