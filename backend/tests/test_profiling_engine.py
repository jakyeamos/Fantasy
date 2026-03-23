from fantasy.profiling.profiling_engine import ProfilingEngine
from fantasy.profiling.models import ExploitationClassification


def test_parse_trade_sides(profiling_seed_data):
    engine = ProfilingEngine(profiling_seed_data)
    trade = engine._load_trades("league_x", 1)[0]
    received, sent, received_picks, sent_picks = engine._parse_trade_sides(trade, 1)
    assert received == ["qb2"]
    assert sent == ["wr1"]
    assert received_picks == []
    assert sent_picks == [1]


def test_compute_value_delta_positive(profiling_seed_data):
    engine = ProfilingEngine(profiling_seed_data)
    adp_map = engine._load_adp_values(["wr1", "wr2"])
    delta = engine._compute_value_delta(["wr1"], ["wr2"], adp_map=adp_map)
    assert delta > 0


def test_compute_value_delta_negative(profiling_seed_data):
    engine = ProfilingEngine(profiling_seed_data)
    adp_map = engine._load_adp_values(["wr1", "qb2"])
    delta = engine._compute_value_delta(["qb2"], ["wr1"], adp_map=adp_map)
    assert delta < 0


def test_compute_value_delta_uses_position_fallback(profiling_seed_data):
    profiling_seed_data.execute(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES ('fallback_player', 'Fallback Player', 'QB', 'Z', 24, '{}')
        ON CONFLICT (player_id) DO NOTHING
        """
    )
    engine = ProfilingEngine(profiling_seed_data)
    adp_map = engine._load_adp_values(["fallback_player"])
    assert adp_map["fallback_player"] > 0


def test_compute_value_delta_uses_pick_values(profiling_seed_data):
    engine = ProfilingEngine(profiling_seed_data)
    delta = engine._compute_value_delta([], [], received_pick_rounds=[1], sent_pick_rounds=[4])
    assert delta > 0


def test_classify_exploitation_primary_value_loss(profiling_seed_data):
    engine = ProfilingEngine(profiling_seed_data)
    trades = engine._load_trades("league_x", 1)
    player_ids = sorted(
        {
            player_id
            for trade in trades
            for player_id in engine._parse_trade_sides(trade, 1)[0]
            + engine._parse_trade_sides(trade, 1)[1]
        }
    )
    classification = engine._classify_exploitation(
        trades,
        1,
        "hard_rebuild",
        engine._load_adp_values(player_ids),
    )
    assert classification.primary_type == "value_loss"


def test_classify_exploitation_secondary_present(profiling_seed_data):
    engine = ProfilingEngine(profiling_seed_data)
    trades = engine._load_trades("league_x", 1)
    player_ids = sorted(
        {
            player_id
            for trade in trades
            for player_id in engine._parse_trade_sides(trade, 1)[0]
            + engine._parse_trade_sides(trade, 1)[1]
        }
    )
    classification = engine._classify_exploitation(
        trades,
        1,
        "hard_rebuild",
        engine._load_adp_values(player_ids),
    )
    assert classification.secondary_type in {
        "archetype_overpay",
        "directional_incoherence",
    }


def test_classify_exploitation_no_secondary_when_below_threshold(phase3_seed_data):
    phase3_seed_data.execute(
        """
        INSERT INTO team_directions (
            id, league_id, roster_id, primary_label, confidence, reasoning,
            alternates_json, delta_json, approved_moves, discouraged_moves
        )
        VALUES (1, 'league_x', 1, 'hard_rebuild', 0.9, 'seeded', '[]', '{}', '[]', '[]')
        ON CONFLICT (league_id, roster_id) DO UPDATE SET
            primary_label = EXCLUDED.primary_label,
            confidence = EXCLUDED.confidence,
            reasoning = EXCLUDED.reasoning,
            alternates_json = EXCLUDED.alternates_json,
            delta_json = EXCLUDED.delta_json,
            approved_moves = EXCLUDED.approved_moves,
            discouraged_moves = EXCLUDED.discouraged_moves
        """
    )
    engine = ProfilingEngine(phase3_seed_data)
    trades = engine._load_trades("league_x", 1)
    player_ids = sorted(
        {
            player_id
            for trade in trades
            for player_id in engine._parse_trade_sides(trade, 1)[0]
            + engine._parse_trade_sides(trade, 1)[1]
        }
    )
    classification = engine._classify_exploitation(
        trades,
        1,
        "hard_rebuild",
        engine._load_adp_values(player_ids),
    )
    assert classification.secondary_type is None


def test_classify_exploitation_detects_directional_incoherence(profiling_seed_data):
    engine = ProfilingEngine(profiling_seed_data)
    trades = engine._load_trades("league_x", 1)
    player_ids = sorted(
        {
            player_id
            for trade in trades
            for player_id in engine._parse_trade_sides(trade, 1)[0]
            + engine._parse_trade_sides(trade, 1)[1]
        }
    )
    classification = engine._classify_exploitation(
        trades,
        1,
        "hard_rebuild",
        engine._load_adp_values(player_ids),
    )
    assert classification.evidence_counts["directional_incoherence"] >= 3


def test_classify_exploitation_handles_missing_direction(profiling_seed_data):
    profiling_seed_data.execute(
        "DELETE FROM team_directions WHERE league_id = 'league_x' AND roster_id = 1"
    )
    engine = ProfilingEngine(profiling_seed_data)
    profile = engine.compute_profile("league_x", 1)
    assert profile.direction_label is None
    assert profile.exploitation_primary is not None


def test_compute_score_range(profiling_seed_data):
    engine = ProfilingEngine(profiling_seed_data)
    profile = engine.compute_profile("league_x", 1)
    assert 0.0 <= profile.exploitability_score <= 100.0


def test_compute_profile_low_confidence_true(phase3_seed_data):
    phase3_seed_data.execute(
        """
        INSERT INTO team_directions (
            id, league_id, roster_id, primary_label, confidence, reasoning,
            alternates_json, delta_json, approved_moves, discouraged_moves
        )
        VALUES (1, 'league_x', 1, 'hard_rebuild', 0.9, 'seeded', '[]', '{}', '[]', '[]')
        ON CONFLICT (league_id, roster_id) DO UPDATE SET
            primary_label = EXCLUDED.primary_label,
            confidence = EXCLUDED.confidence,
            reasoning = EXCLUDED.reasoning,
            alternates_json = EXCLUDED.alternates_json,
            delta_json = EXCLUDED.delta_json,
            approved_moves = EXCLUDED.approved_moves,
            discouraged_moves = EXCLUDED.discouraged_moves
        """
    )
    engine = ProfilingEngine(phase3_seed_data)
    profile = engine.compute_profile("league_x", 1)
    assert profile.low_confidence is True


def test_compute_profile_low_confidence_false(profiling_seed_data):
    engine = ProfilingEngine(profiling_seed_data)
    profile = engine.compute_profile("league_x", 1)
    assert profile.low_confidence is False


def test_compute_pitch_angles_count(profiling_seed_data):
    engine = ProfilingEngine(profiling_seed_data)
    profile = engine.compute_profile("league_x", 1)
    assert 2 <= len(profile.pitch_angles) <= 3


def test_compute_pitch_angles_distinguish_rebuild_from_contender_context(phase3_seed_data):
    engine = ProfilingEngine(phase3_seed_data)
    exploitation = ExploitationClassification(
        primary_type="value_loss",
        secondary_type="timing_error",
        evidence_strings={},
        evidence_counts={"value_loss": 6, "timing_error": 4},
        metadata={
            "avg_delta": -0.18,
            "sent_pick_trades": 2,
            "trade_count": 10,
        },
    )

    rebuild_angles = engine._compute_pitch_angles(exploitation, "hard_rebuild")
    contender_angles = engine._compute_pitch_angles(exploitation, "true_contender")

    assert rebuild_angles[0].deal_archetype != contender_angles[0].deal_archetype


def test_compute_pitch_angles_use_pick_leak_copy_for_rebuild_context(phase3_seed_data):
    engine = ProfilingEngine(phase3_seed_data)
    angles = engine._compute_pitch_angles(
        ExploitationClassification(
            primary_type="value_loss",
            secondary_type="directional_incoherence",
            evidence_strings={},
            evidence_counts={"value_loss": 7, "directional_incoherence": 4},
            metadata={
                "avg_delta": -0.22,
                "sent_pick_trades": 3,
                "trade_count": 12,
            },
        ),
        "hard_rebuild",
    )

    assert angles[0].deal_archetype in {"Future-flex buyback", "Pick-leak recovery"}
    assert "future" in angles[0].reasoning.lower() or "pick" in angles[0].reasoning.lower()


def test_compute_pitch_angles_personalize_position_specific_overpay_copy(phase3_seed_data):
    engine = ProfilingEngine(phase3_seed_data)
    angles = engine._compute_pitch_angles(
        ExploitationClassification(
            primary_type="archetype_overpay",
            secondary_type=None,
            evidence_strings={},
            evidence_counts={"archetype_overpay": 4, "value_loss": 2},
            metadata={
                "avg_delta": -0.12,
                "focus_position": "RB",
                "sent_pick_trades": 0,
                "trade_count": 8,
            },
        ),
        "true_contender",
    )

    assert "RB" in angles[0].deal_archetype
    assert "RB" in angles[0].reasoning or "RB" in angles[0].send_description


def test_evidence_strings_format(profiling_seed_data):
    engine = ProfilingEngine(profiling_seed_data)
    profile = engine.compute_profile("league_x", 1)
    assert profile.exploitation_evidence["value_loss"].startswith("Lost value on")
    assert "trades contradict hard_rebuild direction" in profile.exploitation_evidence["directional_incoherence"]


def test_compute_profile_prefers_owner_display_name(profiling_seed_data):
    profiling_seed_data.execute(
        """
        UPDATE rosters
        SET owner_display_name = 'Display Alpha'
        WHERE league_id = 'league_x' AND roster_id = 1
        """
    )
    engine = ProfilingEngine(profiling_seed_data)
    profile = engine.compute_profile("league_x", 1)
    assert profile.manager_name == "Display Alpha"


def test_trade_history_uses_pick_season_from_payload(profiling_seed_data):
    engine = ProfilingEngine(profiling_seed_data)
    profile = engine.compute_profile("league_x", 1)
    assert any(
        "2026 Round 1 pick" in asset for trade in profile.trade_history for asset in trade["sent_assets"]
    )


def test_rebuild_pitch_logic_accepts_current_direction_labels(profiling_seed_data):
    engine = ProfilingEngine(profiling_seed_data)
    trades = engine._load_trades("league_x", 1)
    player_ids = sorted(
        {
            player_id
            for trade in trades
            for player_id in engine._parse_trade_sides(trade, 1)[0]
            + engine._parse_trade_sides(trade, 1)[1]
        }
    )
    classification = engine._classify_exploitation(
        trades,
        1,
        "one_year_punt",
        engine._load_adp_values(player_ids),
    )
    assert classification.evidence_counts["directional_incoherence"] >= 1
