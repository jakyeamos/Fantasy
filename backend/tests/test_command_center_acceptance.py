from __future__ import annotations

import json

from fantasy.actions.command_center import CommandCenterEngine
from fantasy.actions.models import CommandAction
from fantasy.lineup.lineup_repo import LineupRepo
from fantasy.lineup.models import LineupResult, LineupSlotScore
from fantasy.trends.models import OpportunityCta, OpportunityFeedItem
from fantasy.waiver.models import WaiverRecommendation, WaiverRecommendationsResponse
from fantasy.waiver.waiver_repo import WaiverRepo


def _action(
    action_id: str,
    category: str,
    urgency: str,
    confidence: str,
    rank: int,
) -> CommandAction:
    return CommandAction(
        id=action_id,
        league_id="cmd5",
        roster_id=1,
        category=category,
        priority_rank=rank,
        urgency=urgency,
        confidence=confidence,
        headline=f"{category.title()} move {rank}",
        recommended_action="Send the offer at a fair price before waivers process.",
        why_now="The market window is open today.",
        risk_if_wrong="The role signal can reverse after injury news.",
        evidence=["Price: fair", "Risk: monitored", "CTA: ready"],
        cta_label="Open Decision",
        cta_destination=f"/decision/{rank}",
    )


def test_command_center_top_five_moves_are_actionable(db, monkeypatch):
    engine = CommandCenterEngine(db)
    rosters = [{"league_id": "cmd5", "roster_id": 1}]

    monkeypatch.setattr(engine, "_user_rosters", lambda league_id: rosters)
    monkeypatch.setattr(
        engine,
        "_waiver_actions",
        lambda _: [_action("waiver", "waiver", "today", "HIGH", 3)],
    )
    monkeypatch.setattr(
        engine,
        "_weekly_actions",
        lambda _: [_action("lineup", "lineup", "today", "MEDIUM", 1)],
    )
    monkeypatch.setattr(
        engine,
        "_opportunity_actions",
        lambda league_id: [_action("trade", "trade", "this_week", "HIGH", 2)],
    )
    monkeypatch.setattr(
        engine,
        "_manager_actions",
        lambda _: [_action("manager", "manager", "this_week", "MEDIUM", 4)],
    )
    monkeypatch.setattr(
        engine,
        "_portfolio_actions",
        lambda: [
            _action("portfolio", "portfolio", "watch", "MEDIUM", 5),
            _action("market", "market", "low", "LOW", 6),
        ],
    )

    response = engine.build()

    top_five = response.actions[:5]
    assert len(top_five) == 5
    assert [action.priority_rank for action in top_five] == [1, 2, 3, 4, 5]
    assert top_five[0].urgency == "today"
    for action in top_five:
        assert action.recommended_action
        assert action.why_now
        assert action.risk_if_wrong
        assert action.evidence
        assert action.cta_label
        assert action.cta_destination
    assert {tag.domain for tag in response.data_health} == {
        "injuries",
        "usage",
        "schedule",
        "waivers",
        "market",
        "stats",
    }
    assert response.refresh_actions
    assert any(action.endpoint == "/actions/recompute" for action in response.refresh_actions)
    assert any(
        action.endpoint == "/weekly/league/cmd5/refresh-context"
        for action in response.refresh_actions
    )


def test_command_center_turns_weekly_availability_into_top_move(db):
    db.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions,
            settings_blob, superflex, tep, ppr
        )
        VALUES (
            'cmd_weekly', 'Weekly Command', '2026', '{}',
            '["RB","BN"]', '{}', FALSE, FALSE, 1.0
        )
        """
    )
    db.execute(
        """
        INSERT INTO rosters (
            id, league_id, roster_id, owner_id, owner_display_name,
            starters, players, reserve, taxi
        )
        VALUES (
            1, 'cmd_weekly', 1, 'owner_a', 'Alpha',
            '["rb_out"]', '["rb_out","rb_active"]', '[]', '[]'
        )
        """
    )
    for player_id, name, status in [
        ("rb_out", "Locked Starter", "Out"),
        ("rb_active", "Bench Pivot", "Active"),
    ]:
        db.execute(
            """
            INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
            VALUES (?, ?, 'RB', 'CMD', 25, ?)
            """,
            [player_id, name, json.dumps({"status": status})],
        )
    db.execute(
        """
        INSERT INTO player_stats_weekly (
            player_id, player_name, position, season, week, fantasy_points, carries
        )
        VALUES
            ('rb_out', 'Locked Starter', 'RB', 2026, 1, 15.0, 16.0),
            ('rb_active', 'Bench Pivot', 'RB', 2026, 1, 9.0, 11.0)
        """
    )

    response = CommandCenterEngine(db).build("cmd_weekly")

    assert response.actions
    top = response.actions[0]
    assert top.category == "lineup"
    assert top.urgency == "today"
    assert top.headline == "Weekly Command: start Bench Pivot"
    assert top.recommended_action == "Start Bench Pivot over Locked Starter."
    assert top.risk_if_wrong == (
        "Do not lock this player into a weekly lineup without an availability update."
    )
    assert "injuries" in top.stale_domains
    assert any("Sit availability: out" == evidence for evidence in top.evidence)
    assert any("Weekly data stale: injuries" in evidence for evidence in top.evidence)
    assert top.cta_destination == (
        "/league/cmd_weekly?rosterId=1&focus=weekly"
        "&startPlayerId=rb_active&sitPlayerId=rb_out"
    )


def test_command_center_connects_waiver_add_to_lineup_gap(db):
    db.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions,
            settings_blob, superflex, tep, ppr
        )
        VALUES (
            'cmd_waiver_gap', 'Waiver Gap', '2026', '{}',
            '["WR","BN"]', '{}', FALSE, FALSE, 1.0
        )
        """
    )
    db.execute(
        """
        INSERT INTO rosters (
            id, league_id, roster_id, owner_id, owner_display_name,
            starters, players, reserve, taxi
        )
        VALUES (
            1, 'cmd_waiver_gap', 1, 'owner_a', 'Alpha',
            '["wr_weak"]', '["wr_weak"]', '[]', '[]'
        )
        """
    )
    db.execute(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES ('wr_weak', 'Thin Starter', 'WR', 'GAP', 27, '{"status":"Active"}')
        """
    )
    LineupRepo(db).save_lineup_result(
        LineupResult(
            league_id="cmd_waiver_gap",
            roster_id=1,
            slot_scores=[
                LineupSlotScore(
                    position="WR",
                    player_id="wr_weak",
                    player_name="Thin Starter",
                    starter_value=41.0,
                    replacement_level=35.0,
                    score=0.3,
                    playoff_target=48.0,
                    title_target=55.0,
                    elite_target=62.0,
                    upgrade_leverage_score=0.8,
                    gap_to_playoff_target=7.0,
                    gap_to_title_target=14.0,
                    gap_to_elite_target=21.0,
                    below_playoff_target=True,
                    below_title_target=True,
                    below_elite_target=True,
                    weak_relative_to_contender=True,
                    benchmark_used=True,
                    benchmark_sample_size=12,
                )
            ],
            total_lineup_score=41.0,
            overall_playoff_target=48.0,
            overall_title_target=55.0,
            overall_elite_target=62.0,
            overall_gap_to_playoff_target=7.0,
            overall_gap_to_title_target=14.0,
            overall_gap_to_elite_target=21.0,
            title_window_label="Fading Window",
            title_window_composite=0.45,
            ceiling_score=0.4,
            stability_score=0.3,
            depth_score=0.2,
        )
    )
    WaiverRepo(db).upsert_waiver_recommendations(
        WaiverRecommendationsResponse(
            league_id="cmd_waiver_gap",
            roster_id=1,
            waiver_type_label="faab",
            waiver_type_raw=2,
            remaining_faab=72,
            total_faab=100,
            computed_at="2026-06-28T00:00:00+00:00",
            recommendations=[
                WaiverRecommendation(
                    player_id="wr_add",
                    player_name="Lineup Fix WR",
                    position="WR",
                    recommendation_label="faab_bid",
                    bid_low=8,
                    bid_mid=12,
                    bid_high=16,
                    urgency="Medium",
                    confidence="HIGH",
                    rationale="Best available WR with a cleaner weekly role.",
                    is_immediate_start=True,
                    drop_candidate="Thin Starter",
                    drop_reason="Thin Starter is below the title lineup target.",
                    roster_fit="Immediate WR starter patch",
                )
            ],
        )
    )

    response = CommandCenterEngine(db).build("cmd_waiver_gap")

    assert response.actions
    waiver_action = response.actions[0]
    assert waiver_action.category == "waiver"
    assert waiver_action.urgency == "today"
    assert waiver_action.headline == "Waiver Gap: add Lineup Fix WR"
    assert "fixes a current WR lineup gap" in waiver_action.why_now
    assert any(
        evidence == "Weekly lineup gap: WR is 14.0 below the title target"
        for evidence in waiver_action.evidence
    )


def test_command_center_connects_buy_window_to_lineup_gap(db, monkeypatch):
    db.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions,
            settings_blob, superflex, tep, ppr
        )
        VALUES ('cmd_trade_gap', 'Trade Gap', '2026', '{}', '["WR","BN"]', '{}', FALSE, FALSE, 1.0)
        """
    )
    db.executemany(
        """
        INSERT INTO rosters (
            id, league_id, roster_id, owner_id, owner_display_name,
            starters, players, reserve, taxi
        )
        VALUES (?, 'cmd_trade_gap', ?, ?, ?, ?, ?, '[]', '[]')
        """,
        [
            (1, 1, "owner_a", "Alpha", '["weak_wr"]', json.dumps(["weak_wr", "send_wr"])),
            (2, 2, "owner_b", "Beta", '["target_wr"]', json.dumps(["target_wr"])),
        ],
    )
    db.executemany(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES (?, ?, 'WR', 'TG', 25, '{"status":"Active"}')
        """,
        [
            ("weak_wr", "Thin Starter",),
            ("send_wr", "Send WR",),
            ("target_wr", "Target WR",),
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
        VALUES (?, 'cmd_trade_gap', ?, ?, ?, 0.5, 0.5, 0.5, 0.5, ?, 0.5, 0.5, ?, 0.5, 0.5, 0.5, ?, ?, 0.5, 0.5, 0.5)
        """,
        [
            (1, 1, "weak_wr", 0.40, 0.40, 0.40, 0.40, 0.40),
            (2, 1, "send_wr", 0.56, 0.56, 0.56, 0.56, 0.56),
            (3, 2, "target_wr", 0.68, 0.68, 0.68, 0.68, 0.68),
        ],
    )
    LineupRepo(db).save_lineup_result(
        LineupResult(
            league_id="cmd_trade_gap",
            roster_id=1,
            slot_scores=[
                LineupSlotScore(
                    position="WR",
                    player_id="weak_wr",
                    player_name="Thin Starter",
                    starter_value=43.0,
                    replacement_level=35.0,
                    score=0.35,
                    playoff_target=49.0,
                    title_target=56.0,
                    elite_target=63.0,
                    upgrade_leverage_score=0.9,
                    gap_to_playoff_target=6.0,
                    gap_to_title_target=13.0,
                    gap_to_elite_target=20.0,
                    below_playoff_target=True,
                    below_title_target=True,
                    below_elite_target=True,
                    weak_relative_to_contender=True,
                    benchmark_used=True,
                    benchmark_sample_size=12,
                )
            ],
            total_lineup_score=43.0,
            overall_playoff_target=49.0,
            overall_title_target=56.0,
            overall_elite_target=63.0,
            overall_gap_to_playoff_target=6.0,
            overall_gap_to_title_target=13.0,
            overall_gap_to_elite_target=20.0,
            title_window_label="Fading Window",
            title_window_composite=0.45,
            ceiling_score=0.4,
            stability_score=0.3,
            depth_score=0.2,
        )
    )

    class FakeOpportunityEngine:
        def __init__(self, _conn):
            pass

        def build_feed(self):
            return [
                OpportunityFeedItem(
                    player_id="target_wr",
                    player_name="Target WR",
                    position="WR",
                    trend_label="will_rise",
                    trend_confidence="HIGH",
                    adp_gap=-24.0,
                    suggested_action="buy",
                    availability="opponent_roster",
                    impact_score=88.0,
                    why_summary="Target WR is underpriced before usage catches up.",
                    cta=OpportunityCta(
                        label="Build offer",
                        destination="trade_evaluator",
                        league_id="cmd_trade_gap",
                        user_roster_id=1,
                        manager_roster_id=2,
                    ),
                )
            ]

    monkeypatch.setattr("fantasy.actions.command_center.OpportunityEngine", FakeOpportunityEngine)

    response = CommandCenterEngine(db).build("cmd_trade_gap")

    trade_action = next(action for action in response.actions if action.id == "market:target_wr")
    assert trade_action.category == "trade"
    assert trade_action.urgency == "today"
    assert "solves a current WR lineup gap" in trade_action.why_now
    assert "usage" in trade_action.stale_domains
    assert any(
        evidence == "Weekly lineup gap: WR is 13.0 below the title target"
        for evidence in trade_action.evidence
    )
    assert trade_action.trade_suggestion is not None
    assert "sendPlayerId=send_wr" in trade_action.cta_destination
    assert "receivePlayerId=target_wr" in trade_action.cta_destination


def test_command_center_escalates_injured_portfolio_exposure(db):
    db.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions,
            settings_blob, superflex, tep, ppr
        )
        VALUES
            ('portfolio_a', 'Portfolio A', '2026', '{}', '[]', '{}', FALSE, FALSE, 1.0),
            ('portfolio_b', 'Portfolio B', '2026', '{}', '[]', '{}', FALSE, FALSE, 1.0)
        """
    )
    db.executemany(
        """
        INSERT INTO rosters (
            id, league_id, roster_id, owner_id, owner_display_name,
            starters, players, reserve, taxi
        )
        VALUES (?, ?, 1, 'portfolio_owner', 'Portfolio Owner', '[]', ?, '[]', '[]')
        """,
        [
            (1, "portfolio_a", json.dumps(["injured_wr"])),
            (2, "portfolio_b", json.dumps(["injured_wr"])),
        ],
    )
    db.execute(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES (?, 'Injured Anchor', 'WR', 'BUF', 27, ?)
        """,
        ["injured_wr", json.dumps({"status": "Out"})],
    )

    response = CommandCenterEngine(db).build()

    action = next(
        item for item in response.actions if item.id == "portfolio:exposure:injured_wr"
    )
    assert action.urgency == "today"
    assert action.confidence == "HIGH"
    assert action.recommended_action == (
        "Hedge Injured Anchor now: shop one share or add a direct backup plan before lineups lock."
    )
    assert action.risk_if_wrong == (
        "Hedging an injured player can cost upside if availability clears faster than the market expects."
    )
    assert action.stale_domains == ["injuries"]
    assert "availability is out" in action.why_now
    assert any(evidence == "Availability: out" for evidence in action.evidence)
    assert any(
        evidence == "News dependency: confirm injury status before locking portfolio exposure"
        for evidence in action.evidence
    )
    assert action.cta_destination == "/portfolio?playerId=injured_wr"
