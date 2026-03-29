from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from fantasy.profiling.models import ExploitationClassification, ManagerProfile
from fantasy.profiling.profiling_engine import ProfilingEngine


def _seed_league(conn) -> None:
    conn.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions,
            settings_blob, superflex, tep, ppr
        )
        VALUES (
            'league_behavior',
            'League Behavior',
            '2026',
            '{"rec":1.0}',
            '["QB","RB","WR","TE","BN"]',
            '{"num_teams":2}',
            FALSE,
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
            (1, 'league_behavior', 1, 'user_a', 'Manager A', '[]', '["vet1","young1"]', '[]', '[]'),
            (2, 'league_behavior', 2, 'user_b', 'Manager B', '[]', '[]', '[]', '[]')
        """
    )


def _patch_engine(monkeypatch, engine: ProfilingEngine, *, trades, direction, exploitation):
    monkeypatch.setattr(engine, "_load_trades", lambda league_id, roster_id: trades)
    monkeypatch.setattr(engine, "_load_adp_values", lambda player_ids: {})
    monkeypatch.setattr(engine, "_load_direction", lambda league_id, roster_id: direction)
    monkeypatch.setattr(
        engine,
        "_classify_exploitation",
        lambda trades, roster_id, direction, adp_map: exploitation,
    )
    monkeypatch.setattr(engine, "_compute_score", lambda total, exploitation: 42.0)
    monkeypatch.setattr(engine, "_compute_pitch_angles", lambda exploitation, direction: [])
    monkeypatch.setattr(engine, "_build_trade_history", lambda trades, roster_id, adp_map: [])
    monkeypatch.setattr(
        engine,
        "_parse_trade_sides",
        lambda trade, roster_id: (
            trade.get("received", []),
            trade.get("sent", []),
            trade.get("received_picks", []),
            trade.get("sent_picks", []),
        ),
    )
    monkeypatch.setattr(engine, "_compute_value_delta", lambda *args, **kwargs: -0.2)
    monkeypatch.setattr(
        engine,
        "_load_player_ages",
        lambda player_ids: {
            player_id: 28 if player_id.startswith("vet") else 22 for player_id in player_ids
        },
    )


def test_compute_profile_with_no_trades_defaults_behavior_fields(db, monkeypatch) -> None:
    _seed_league(db)
    engine = ProfilingEngine(db)
    _patch_engine(
        monkeypatch,
        engine,
        trades=[],
        direction="hard_rebuild",
        exploitation=ExploitationClassification(
            primary_type=None,
            secondary_type=None,
            evidence_strings={},
            evidence_counts={},
            metadata={},
        ),
    )

    profile = engine.compute_profile("league_behavior", 1)

    assert profile.recent_urgency_state == "stable"
    assert profile.veteran_appetite == 0.0
    assert profile.value_rigidity == 0.0
    assert "Insufficient trade evidence" in (profile.likely_motivations_now or "")
    assert profile.best_asset_to_target is None
    assert profile.best_asset_to_send is None


def test_compute_profile_building_urgency_for_rebuilder_sending_picks(db, monkeypatch) -> None:
    _seed_league(db)
    engine = ProfilingEngine(db)
    trades = [
        {"week": 2, "received": ["young1"], "sent": ["vet1"], "sent_picks": [1]},
        {"week": 3, "received": ["young1"], "sent": ["vet1"], "sent_picks": [1]},
        {"week": 7, "received": ["young1"], "sent": ["vet1"], "sent_picks": [2]},
    ]
    exploitation = ExploitationClassification(
        primary_type="value_loss",
        secondary_type=None,
        evidence_strings={},
        evidence_counts={"value_loss": 3, "timing_error": 0, "archetype_overpay": 0},
        metadata={"avg_delta": -0.1, "win_rate": 0.2, "sent_pick_trades": 3, "trade_count": 3},
    )
    _patch_engine(monkeypatch, engine, trades=trades, direction="hard_rebuild", exploitation=exploitation)

    profile = engine.compute_profile("league_behavior", 1)

    assert profile.recent_urgency_state == "building_urgency"
    assert profile.reroute_susceptibility > 0.5


def test_compute_profile_panic_mode_for_contender_losing_value(db, monkeypatch) -> None:
    _seed_league(db)
    engine = ProfilingEngine(db)
    trades = [{"week": 8, "received": ["young1"], "sent": ["vet1"]}] * 4
    exploitation = ExploitationClassification(
        primary_type="value_loss",
        secondary_type=None,
        evidence_strings={},
        evidence_counts={"value_loss": 4, "timing_error": 0, "archetype_overpay": 0},
        metadata={"avg_delta": -0.2, "win_rate": 0.25, "sent_pick_trades": 0, "trade_count": 4},
    )
    _patch_engine(monkeypatch, engine, trades=trades, direction="true_contender", exploitation=exploitation)

    profile = engine.compute_profile("league_behavior", 1)

    assert profile.recent_urgency_state == "panic_mode"


def test_compute_profile_declining_window_when_contender_win_rate_slips(db, monkeypatch) -> None:
    _seed_league(db)
    engine = ProfilingEngine(db)
    trades = [{"week": 8, "received": ["young1"], "sent": ["vet1"]}] * 5
    exploitation = ExploitationClassification(
        primary_type="value_loss",
        secondary_type=None,
        evidence_strings={},
        evidence_counts={"value_loss": 2, "timing_error": 0, "archetype_overpay": 0},
        metadata={"avg_delta": -0.05, "win_rate": 0.39, "sent_pick_trades": 0, "trade_count": 5},
    )
    _patch_engine(monkeypatch, engine, trades=trades, direction="true_contender", exploitation=exploitation)

    profile = engine.compute_profile("league_behavior", 1)

    assert profile.recent_urgency_state == "declining_window"


def test_compute_profile_rookie_fever_index_rises_for_wr_overpay(db, monkeypatch) -> None:
    _seed_league(db)
    engine = ProfilingEngine(db)
    trades = [{"week": 8, "received": ["young1"], "sent": ["vet1"]}] * 5
    exploitation = ExploitationClassification(
        primary_type="archetype_overpay",
        secondary_type=None,
        evidence_strings={},
        evidence_counts={"value_loss": 0, "timing_error": 0, "archetype_overpay": 3},
        metadata={"avg_delta": -0.05, "win_rate": 0.4, "sent_pick_trades": 0, "trade_count": 5, "focus_position": "WR"},
    )
    _patch_engine(monkeypatch, engine, trades=trades, direction="hard_rebuild", exploitation=exploitation)

    profile = engine.compute_profile("league_behavior", 1)

    assert profile.rookie_fever_index > 0.4


def test_compute_profile_value_rigidity_rises_with_value_loss_and_timing_error(db, monkeypatch) -> None:
    _seed_league(db)
    engine = ProfilingEngine(db)
    trades = [{"week": 8, "received": ["young1"], "sent": ["vet1"]}] * 5
    exploitation = ExploitationClassification(
        primary_type="value_loss",
        secondary_type="timing_error",
        evidence_strings={},
        evidence_counts={"value_loss": 3, "timing_error": 2, "archetype_overpay": 0},
        metadata={"avg_delta": -0.12, "win_rate": 0.2, "sent_pick_trades": 0, "trade_count": 5},
    )
    _patch_engine(monkeypatch, engine, trades=trades, direction="true_contender", exploitation=exploitation)

    profile = engine.compute_profile("league_behavior", 1)

    assert profile.value_rigidity >= 0.5


def test_best_asset_to_target_is_none_when_low_confidence(db, monkeypatch) -> None:
    _seed_league(db)
    engine = ProfilingEngine(db)
    trades = [{"week": 8, "received": ["young1"], "sent": ["vet1"]}] * 2
    exploitation = ExploitationClassification(
        primary_type="value_loss",
        secondary_type=None,
        evidence_strings={},
        evidence_counts={"value_loss": 2, "timing_error": 0, "archetype_overpay": 0},
        metadata={"avg_delta": -0.2, "win_rate": 0.2, "sent_pick_trades": 0, "trade_count": 2},
    )
    _patch_engine(monkeypatch, engine, trades=trades, direction="true_contender", exploitation=exploitation)

    profile = engine.compute_profile("league_behavior", 1)

    assert profile.best_asset_to_target is None


def test_best_asset_to_send_reflects_focus_position_for_archetype_overpay(db, monkeypatch) -> None:
    _seed_league(db)
    engine = ProfilingEngine(db)
    trades = [{"week": 8, "received": ["young1"], "sent": ["vet1"]}] * 10
    exploitation = ExploitationClassification(
        primary_type="archetype_overpay",
        secondary_type=None,
        evidence_strings={},
        evidence_counts={"value_loss": 0, "timing_error": 0, "archetype_overpay": 4},
        metadata={"avg_delta": -0.05, "win_rate": 0.5, "sent_pick_trades": 0, "trade_count": 10, "focus_position": "WR"},
    )
    _patch_engine(monkeypatch, engine, trades=trades, direction="hard_rebuild", exploitation=exploitation)

    profile = engine.compute_profile("league_behavior", 1)

    assert profile.best_asset_to_send is not None
    assert "WR" in profile.best_asset_to_send


def test_recent_urgency_state_literal_is_enforced() -> None:
    with pytest.raises(ValidationError):
        ManagerProfile(
            league_id="league_behavior",
            roster_id=1,
            computed_at=datetime.now(tz=timezone.utc).isoformat(),
            manager_name="Manager A",
            direction_label="hard_rebuild",
            evidence_count=0,
            low_confidence=True,
            exploitability_score=0.0,
            exploitation_primary=None,
            exploitation_secondary=None,
            exploitation_evidence={},
            pitch_angles=[],
            aggregate_trade_stats={"total_trades": 0, "win_rate": 0.0, "avg_delta": 0.0},
            recent_urgency_state="invalid",  # type: ignore[arg-type]
        )
