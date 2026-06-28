from __future__ import annotations

import json

from fantasy.actions.command_center import CommandCenterEngine
from fantasy.actions.models import CommandAction
from fantasy.lineup.lineup_repo import LineupRepo
from fantasy.lineup.models import LineupResult, LineupSlotScore
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
