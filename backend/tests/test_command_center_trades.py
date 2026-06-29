from __future__ import annotations

import json

from fantasy.actions.trade_suggestions import TradeSuggestionBuilder
from fantasy.trends.models import OpportunityCta, OpportunityFeedItem


def test_trade_suggestion_uses_real_roster_assets(db):
    db.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions,
            settings_blob, superflex, tep, ppr
        )
        VALUES ('trade_cmd', 'Trade Command', '2026', '{}', '[]', '{}', FALSE, FALSE, 1.0)
        """
    )
    db.executemany(
        """
        INSERT INTO rosters (
            id, league_id, roster_id, owner_id, owner_display_name,
            starters, players, reserve, taxi
        )
        VALUES (?, 'trade_cmd', ?, ?, ?, '[]', ?, '[]', '[]')
        """,
        [
            (1, 1, "user", "User", json.dumps(["send_wr", "bench_rb"])),
            (2, 2, "opp", "Opponent", json.dumps(["target_wr", "small_te"])),
        ],
    )
    db.executemany(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES (?, ?, ?, 'X', 25, '{}')
        """,
        [
            ("send_wr", "Send WR", "WR"),
            ("bench_rb", "Bench RB", "RB"),
            ("target_wr", "Target WR", "WR"),
            ("small_te", "Small TE", "TE"),
        ],
    )
    db.executemany(
        """
        INSERT INTO player_values (
            id, league_id, roster_id, player_id,
            comp_current_production, comp_short_term, comp_role_stability,
            comp_age_curve, comp_insulation, comp_market_liquidity,
            comp_positional_scarcity, comp_fragility, comp_ceiling, comp_floor,
            comp_rerollability, comp_contract, lens_production, lens_market,
            lens_insulation, lens_team_fit, lens_direction
        )
        VALUES (
            ?, 'trade_cmd', ?, ?, ?, 0.5, 0.5, 0.5, 0.5, ?, 0.5, 0.5, ?,
            0.5, 0.5, 0.5, ?, ?, 0.5, 0.5, 0.5
        )
        """,
        [
            (1, 1, "send_wr", 0.62, 0.65, 0.63, 0.62, 0.64),
            (2, 1, "bench_rb", 0.35, 0.35, 0.35, 0.35, 0.35),
            (3, 2, "target_wr", 0.72, 0.72, 0.72, 0.72, 0.72),
            (4, 2, "small_te", 0.18, 0.18, 0.18, 0.18, 0.18),
        ],
    )
    db.execute(
        """
        INSERT INTO manager_pitch_angles (
            id, league_id, roster_id, rank, deal_archetype, send_description,
            avoid_description, reasoning
        )
        VALUES (
            1, 'trade_cmd', 2, 1, 'Need solver', 'usable weekly points',
            'fragile futures', 'They have accepted production-first offers.'
        )
        """
    )
    item = OpportunityFeedItem(
        player_id="target_wr",
        player_name="Target WR",
        position="WR",
        trend_label="will_rise",
        trend_confidence="HIGH",
        adp_gap=18.0,
        suggested_action="buy",
        availability="opponent_roster",
        impact_score=80.0,
        why_summary="Target is underpriced.",
        cta=OpportunityCta(
            label="Build offer",
            destination="trade_evaluator",
            league_id="trade_cmd",
            user_roster_id=1,
            manager_roster_id=2,
        ),
    )

    suggestion = TradeSuggestionBuilder(db).build(item)
    assert suggestion is not None
    assert suggestion.send_player_ids == ["send_wr"]
    assert suggestion.receive_player_ids[0] == "target_wr"
    assert suggestion.send_assets == ["Send WR (WR)"]
    assert "usable weekly points" in suggestion.manager_pitch_angle
    assert suggestion.evaluation_score is not None
    assert suggestion.evaluation_verdict in {"send", "counter", "avoid"}
    assert suggestion.evaluation_summary is not None


def test_manager_suggestion_avoids_scarce_tep_te_for_surplus_qb(db):
    db.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions,
            settings_blob, superflex, tep, ppr
        )
        VALUES (
            'trade_tep', 'TE Premium', '2026', '{"bonus_rec_te":0.5}',
            '["QB","RB","WR","TE","SUPER_FLEX","BN","BN","BN"]',
            '{"num_teams":12}', TRUE, TRUE, 1.0
        )
        """
    )
    db.executemany(
        """
        INSERT INTO rosters (
            id, league_id, roster_id, owner_id, owner_display_name,
            starters, players, reserve, taxi
        )
        VALUES (?, 'trade_tep', ?, ?, ?, '[]', ?, '[]', ?)
        """,
        [
            (
                1,
                1,
                "user",
                "User",
                json.dumps(["start_qb", "bench_qb", "loveland", "start_wr", "send_wr", "spare_wr"]),
                json.dumps(["taxi_qb"]),
            ),
            (
                2,
                2,
                "opp",
                "Opponent",
                json.dumps(["target_qb", "target_wr"]),
                json.dumps([]),
            ),
        ],
    )
    db.executemany(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES (?, ?, ?, 'TST', 24, '{}')
        """,
        [
            ("start_qb", "Start QB", "QB"),
            ("bench_qb", "Bench QB", "QB"),
            ("taxi_qb", "Taxi QB", "QB"),
            ("loveland", "Colston Loveland", "TE"),
            ("start_wr", "Start WR", "WR"),
            ("send_wr", "Send WR", "WR"),
            ("spare_wr", "Spare WR", "WR"),
            ("target_qb", "Target QB", "QB"),
            ("target_wr", "Target WR", "WR"),
        ],
    )
    db.executemany(
        """
        INSERT INTO player_values (
            id, league_id, roster_id, player_id,
            comp_current_production, comp_short_term, comp_role_stability,
            comp_age_curve, comp_insulation, comp_market_liquidity,
            comp_positional_scarcity, comp_fragility, comp_ceiling, comp_floor,
            comp_rerollability, comp_contract, lens_production, lens_market,
            lens_insulation, lens_team_fit, lens_direction
        )
        VALUES (
            ?, 'trade_tep', ?, ?, ?, 0.5, 0.5, 0.5, 0.5, ?, ?, 0.5, ?,
            0.5, 0.5, 0.5, ?, ?, 0.5, 0.5, 0.5
        )
        """,
        [
            (1, 1, "start_qb", 0.70, 0.70, 0.55, 0.70, 0.70, 0.70),
            (2, 1, "bench_qb", 0.55, 0.55, 0.50, 0.55, 0.55, 0.55),
            (3, 1, "taxi_qb", 0.35, 0.35, 0.45, 0.35, 0.35, 0.35),
            (4, 1, "loveland", 0.66, 0.66, 0.90, 0.66, 0.66, 0.66),
            (5, 1, "start_wr", 0.60, 0.60, 0.50, 0.60, 0.60, 0.60),
            (6, 1, "send_wr", 0.51, 0.51, 0.45, 0.51, 0.51, 0.51),
            (7, 1, "spare_wr", 0.30, 0.30, 0.30, 0.30, 0.30, 0.30),
            (8, 2, "target_qb", 0.78, 0.78, 0.55, 0.78, 0.78, 0.78),
            (9, 2, "target_wr", 0.62, 0.62, 0.50, 0.62, 0.62, 0.62),
        ],
    )

    suggestion = TradeSuggestionBuilder(db).build_manager_suggestion(
        league_id="trade_tep",
        user_roster_id=1,
        target_roster_id=2,
        confidence="MEDIUM",
        manager_pitch_angle="open with usable points.",
    )

    assert suggestion is not None
    assert suggestion.send_player_ids == ["send_wr"]
    assert suggestion.receive_player_ids == ["target_wr"]
