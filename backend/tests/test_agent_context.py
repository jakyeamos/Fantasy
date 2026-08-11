from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import duckdb
import pytest

from fantasy.agent_context import (
    _parser,
    build_agent_context,
    should_ground_question,
    should_use_roster_subject,
)
from fantasy.advisor import create_recorded_advice, record_presented_packets
from test_support.schema_sql import SCHEMA_SQL


def _seed_burrow_context(db) -> None:
    db.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions,
            settings_blob, superflex, tep, ppr, ingested_at
        )
        VALUES
            ('amg', 'AMG', '2026', '{}',
             '["QB","RB","WR","TE","SUPER_FLEX","BN"]',
             '{"num_teams":12,"draft_rounds":3}', TRUE, TRUE, 0.5,
             '2026-08-01 15:23:48'),
            ('loft', 'The Loft', '2026', '{}',
             '["QB","RB","WR","TE","SUPER_FLEX","BN"]',
             '{"num_teams":12,"draft_rounds":3}', TRUE, TRUE, 0.5,
             '2026-08-01 15:19:21')
        """
    )
    db.execute(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES
            ('6770', 'Joe Burrow', 'QB', 'CIN', 29, '{}'),
            ('tlaw', 'Trevor Lawrence', 'QB', 'JAX', 26, '{}')
        """
    )
    db.execute(
        """
        INSERT INTO rosters (
            id, league_id, roster_id, owner_id, owner_display_name,
            starters, players, reserve, taxi, ingested_at
        )
        VALUES
            (1, 'amg', 1, 'jakye-id', 'jakye', '["6770"]',
             '["6770","tlaw"]', '[]', '[]', '2026-08-01 15:23:48'),
            (2, 'amg', 8, 'other-id', 'Other Manager', '[]',
             '[]', '[]', '[]', '2026-08-01 15:23:48'),
            (3, 'loft', 5, 'bobby-id', 'bobbyhess', '["6770"]',
             '["6770"]', '[]', '[]', '2026-08-01 15:19:21')
        """
    )
    db.execute(
        """
        INSERT INTO standings (
            id, league_id, roster_id, wins, losses, ties, fpts, fpts_against, ingested_at
        )
        VALUES (1, 'amg', 1, 0, 0, 0, 0, 0, '2026-08-01 15:23:48')
        """
    )
    db.execute(
        """
        INSERT INTO team_directions (
            id, league_id, roster_id, computed_at, primary_label, confidence,
            reasoning, alternates_json, delta_json, approved_moves, discouraged_moves
        )
        VALUES (
            1, 'amg', 1, '2026-08-01 15:33:30', 'soft_rebuild', 0.315,
            'Future value and pick capital are high.', '[]', '{}',
            '["buy_rookie_picks"]', '["short_term_patchwork"]'
        )
        """
    )
    db.execute(
        """
        INSERT INTO team_scorecards (
            id, league_id, roster_id, computed_at, win_now, future_value, depth,
            pick_capital, flexibility, fragility, age_risk, liquidity,
            positional_insulation, composite, computation_json
        )
        VALUES (
            1, 'amg', 1, '2026-08-01 15:33:30', 1, 1, 0.08,
            1, 0, 0.57, 0.9, 0.75, 0.5, 0.645, '{}'
        )
        """
    )
    db.execute(
        """
        INSERT INTO traded_picks (
            id, league_id, season, round, roster_id, owner_id, previous_owner_id
        )
        VALUES (1, 'amg', '2026', 1, 8, '1', '8')
        """
    )
    db.execute(
        """
        INSERT INTO pick_values (
            id, league_id, pick_owner_roster_id, pick_year, pick_round,
            computed_at, expected_draft_slot, base_value, timed_value,
            league_adjusted_value, demand_adjusted_value, timing_label,
            timing_reasoning, class_strength_signal, years_out, computation_json
        )
        VALUES (
            1, 'amg', 8, 2026, 1, '2026-08-01 15:33:30', 2,
            90, 90, 95, 95, 'hold_until_rookie_fever', 'Test value', 0, 0, '{}'
        )
        """
    )
    db.execute(
        """
        INSERT INTO ingest_runs (
            id, league_id, run_type, status, started_at, completed_at
        )
        VALUES (
            1, 'amg', 'full', 'complete',
            '2026-08-01 15:23:47', '2026-08-01 15:27:54'
        )
        """
    )


def test_burrow_question_uses_configured_owner_and_matching_league(db):
    _seed_burrow_context(db)

    result = build_agent_context(
        db,
        question="Would you trade Joe Burrow for straight picks?",
        owner_display_name="jakye",
        now=datetime(2026, 8, 3, 12, 0, 0),
    )

    assert result["grounding_recommended"] is True
    assert result["player"]["full_name"] == "Joe Burrow"
    assert [item["league"]["name"] for item in result["leagues"]] == ["AMG"]
    league = result["leagues"][0]
    assert league["league"] == {
        "league_id": "amg",
        "name": "AMG",
        "season": "2026",
        "superflex": True,
        "tep": True,
        "ppr": 0.5,
        "num_teams": 12,
        "draft_rounds": 3,
        "roster_positions": ["QB", "RB", "WR", "TE", "SUPER_FLEX", "BN"],
    }
    assert league["roster"]["owner_display_name"] == "jakye"
    assert {player["full_name"] for player in league["roster"]["players"]} == {
        "Joe Burrow",
        "Trevor Lawrence",
    }
    assert "~1.02" in {
        pick["projected_slot"] for pick in league["roster"]["picks_owned"]
    }
    assert league["team_direction"]["primary_label"] == "soft_rebuild"
    assert league["ingest"]["status"] == "fresh"
    assert result["schema_version"] == "agent-context/2.0"
    assert len(result["decision_packets"]) == 1
    packet = result["decision_packets"][0]
    assert packet["schema_version"] == "decision-packet/1.0"
    assert packet["decision_type"] == "trade"
    assert packet["subject"]["subject_type"] == "player"
    assert packet["interpretation"]["status"] == "underspecified"
    assert packet["recommendation"]["action"] == "request_details"
    assert "pick years" in packet["interpretation"]["missing_details"]
    assert packet["evidence"]["calibration"]["status"] == "unavailable"


def test_agent_context_exposes_live_strength_adjusted_pick_values(db):
    _seed_burrow_context(db)
    db.execute(
        """
        INSERT INTO team_scorecards (
            id, league_id, roster_id, computed_at, win_now, future_value, depth,
            pick_capital, flexibility, fragility, age_risk, liquidity,
            positional_insulation, composite, computation_json
        )
        VALUES (
            2, 'amg', 8, '2026-08-01 15:33:30', 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, '{}'
        )
        """
    )
    db.execute(
        """
        INSERT INTO league_draft_order_rules (
            id, league_id, non_playoff_basis, playoff_ordering, tiebreaker
        )
        VALUES (1, 'amg', 'inverse_standings', 'by_finish', 'points_against')
        """
    )
    db.execute(
        """
        INSERT INTO traded_picks (
            id, league_id, season, round, roster_id, owner_id, previous_owner_id
        )
        VALUES (2, 'amg', '2027', 1, 8, '1', '8')
        """
    )

    result = build_agent_context(
        db,
        question="What are all of my picks worth?",
        owner_display_name="jakye",
        now=datetime(2026, 8, 3, 12, 0, 0),
    )

    picks = result["leagues"][0]["roster"]["picks_owned"]
    strong_owner_pick = next(
        pick
        for pick in picks
        if pick["pick_year"] == 2027 and pick["pick_round"] == 1
        and pick["pick_owner_roster_id"] == 1
    )
    weak_owner_pick = next(
        pick
        for pick in picks
        if pick["pick_year"] == 2027 and pick["pick_round"] == 1
        and pick["pick_owner_roster_id"] == 8
    )

    assert strong_owner_pick["valuation"]["projection_source"] == "team_strength"
    assert weak_owner_pick["valuation"]["projection_source"] == "team_strength"
    assert strong_owner_pick["valuation"]["expected_draft_slot"] > weak_owner_pick["valuation"]["expected_draft_slot"]
    assert strong_owner_pick["valuation"]["league_adjusted_value"] < weak_owner_pick["valuation"]["league_adjusted_value"]


def test_question_routing_distinguishes_roster_decisions_from_trivia():
    assert should_ground_question("Would you trade Joe Burrow for straight picks?") is True
    assert should_ground_question("What is a touchdown?") is False
    assert should_use_roster_subject(
        "Based on my entire roster, what holistic moves should I make?"
    ) is True
    assert should_use_roster_subject("Would you trade Joe Burrow for picks?") is False


def test_broad_roster_question_gets_roster_subject_and_strategy_recommendation(db):
    _seed_burrow_context(db)

    result = build_agent_context(
        db,
        question=(
            "Based on my entire roster, what holistic moves should I recommend "
            "for lineup construction, trades, picks, waivers, and team direction?"
        ),
        owner_display_name="jakye",
        now=datetime(2026, 8, 3, 12, 0, 0),
    )

    assert result["subject"] == {"subject_type": "roster"}
    assert all("No referenced player" not in gap for gap in result["gaps"])
    packet = result["decision_packets"][0]
    assert packet["decision_type"] == "roster"
    assert packet["subject"] == {
        "subject_type": "roster",
        "league_id": "amg",
        "league_name": "AMG",
        "roster_id": 1,
        "owner_id": "jakye-id",
        "owner_display_name": "jakye",
    }
    assert packet["interpretation"]["status"] == "not_applicable"
    assert packet["recommendation"]["action"] == "consider"
    assert packet["recommendation"]["confidence"] > 0


def test_unknown_player_question_does_not_fall_back_to_roster_subject(db):
    _seed_burrow_context(db)

    result = build_agent_context(
        db,
        question="Would you trade Unknown Player for picks?",
        owner_display_name="jakye",
        now=datetime(2026, 8, 3, 12, 0, 0),
    )

    assert result["subject"] is None
    assert "No referenced player matched the local players table." in result["gaps"]
    packet = result["decision_packets"][0]
    assert packet["subject"] is None
    assert packet["recommendation"]["action"] == "insufficient_context"


def test_missing_owner_configuration_is_explicit(db, monkeypatch):
    _seed_burrow_context(db)
    monkeypatch.setattr(
        "fantasy.agent_context.get_settings",
        lambda: SimpleNamespace(
            PORTFOLIO_OWNER_ID=None,
            PORTFOLIO_OWNER_DISPLAY_NAME=None,
        ),
    )

    result = build_agent_context(
        db,
        player_query="Joe Burrow",
        now=datetime(2026, 8, 3, 12, 0, 0),
    )

    assert result["portfolio_owner"] is None
    assert result["leagues"] == []
    assert result["gaps"] == [
        "Portfolio owner is not configured. Set FANTASY_PORTFOLIO_OWNER_ID "
        "or FANTASY_PORTFOLIO_OWNER_DISPLAY_NAME."
    ]


def test_presented_mode_persists_each_generated_packet_without_temp_files(db):
    _seed_burrow_context(db)
    result = build_agent_context(
        db,
        question="Would you trade Joe Burrow for straight picks?",
        owner_display_name="jakye",
        now=datetime(2026, 8, 3, 12, 0, 0),
    )

    recording = record_presented_packets(db, result["decision_packets"])

    assert recording["status"] == "recorded"
    assert recording["event_type"] == "presented"
    assert recording["recorded_packets"] == 1
    assert recording["follow_up_at"] is not None
    row = db.execute(
        "SELECT decision_id, event_type, packet_json FROM decision_feedback"
    ).fetchone()
    assert row[0] == result["decision_packets"][0]["decision_id"]
    assert row[1] == "presented"
    assert '"schema_version":"decision-packet/1.0"' in row[2]


def test_context_cli_rejects_recording_mode():
    with pytest.raises(SystemExit):
        _parser().parse_args(
            [
                "--question",
                "Would you trade Joe Burrow for straight picks?",
                "--record-presented",
            ]
        )


def test_advice_interface_records_presentations_by_default(tmp_path):
    db_path = tmp_path / "advice.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        for statement in SCHEMA_SQL:
            conn.execute(statement)
        _seed_burrow_context(conn)
    finally:
        conn.close()

    result = create_recorded_advice(
        db_path,
        question="Would you trade Joe Burrow for straight picks?",
        owner_display_name="jakye",
        now=datetime(2026, 8, 3, 12, 0, 0),
    )
    repeated_result = create_recorded_advice(
        db_path,
        question="Would you trade Joe Burrow for straight picks?",
        owner_display_name="jakye",
        now=datetime(2026, 8, 3, 12, 0, 0),
    )

    assert result["database"]["mode"] == "read_only_context+append_only_feedback"
    assert result["decision_recording"]["recorded_packets"] == 1
    assert result["decision_recording"]["follow_up_at"] == "2026-09-02 12:00:00"
    assert repeated_result["decision_packets"][0]["decision_id"] == result[
        "decision_packets"
    ][0]["decision_id"]
    assert repeated_result["decision_recording"]["event_ids"] == result[
        "decision_recording"
    ]["event_ids"]
    read_conn = duckdb.connect(str(db_path), read_only=True)
    try:
        assert read_conn.execute(
            "SELECT event_type, resolution_state, CAST(follow_up_at AS VARCHAR) "
            "FROM decision_feedback"
        ).fetchall() == [("presented", "awaiting_action", "2026-09-02 12:00:00")]
    finally:
        read_conn.close()
