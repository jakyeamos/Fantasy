from __future__ import annotations

import json

from fantasy.waiver.models import (
    ActionPlan,
    ActionPlanItem,
    OrphanIntake,
    OrphanIntakeDimension,
    StartupContext,
    StartupPickValuation,
    WaiverRecommendation,
    WaiverRecommendationsResponse,
)
from fantasy.waiver.orphan_engine import OrphanEngine, compute_orphan_composite
from fantasy.waiver.waiver_repo import WaiverRepo


def _seed_orphan_context(db, *, distressed: bool = False) -> None:
    db.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions,
            settings_blob, superflex, tep, ppr
        )
        VALUES (
            'orphan_x',
            'Orphan League',
            '2026',
            '{}',
            '["QB","RB","WR","TE","SUPER_FLEX","BN"]',
            '{"waiver_budget":100,"waiver_type":2}',
            TRUE,
            FALSE,
            1.0
        )
        """
    )
    roster_players = ["p1", "p2", "p3"] if distressed else ["p1", "p2", "p3", "p4"]
    db.execute(
        """
        INSERT INTO rosters (
            id, league_id, roster_id, owner_id, owner_display_name, waiver_position,
            waiver_budget_used, starters, players, reserve, taxi
        )
        VALUES
            (1, 'orphan_x', 1, 'owner_a', 'Alpha', 2, 35, ?, ?, '[]', '[]'),
            (2, 'orphan_x', 2, 'owner_b', 'Beta', 6, 10, '["o1","o2","o3"]', '["o1","o2","o3"]', '[]', '[]')
        """,
        [json.dumps(roster_players[:3]), json.dumps(roster_players)],
    )
    db.execute(
        """
        INSERT INTO team_directions (
            id, league_id, roster_id, primary_label, confidence, reasoning,
            alternates_json, delta_json, approved_moves, discouraged_moves
        )
        VALUES
            (1, 'orphan_x', 1, 'hard_rebuild', 0.9, 'seeded', '[]', '{}', '["acquire_future_first","sell_veterans"]', '[]'),
            (2, 'orphan_x', 2, 'true_contender', 0.9, 'seeded', '[]', '{}', '[]', '[]')
        """
    )
    players = [
        ("p1", "Player One", "WR", 22 if not distressed else 31),
        ("p2", "Player Two", "RB", 23 if not distressed else 30),
        ("p3", "Player Three", "QB", 24 if not distressed else 29),
        ("p4", "Player Four", "TE", 24),
        ("o1", "Other One", "WR", 26),
        ("o2", "Other Two", "RB", 27),
        ("o3", "Other Three", "QB", 25),
        ("fa1", "Waiver One", "WR", 23),
        ("fa2", "Waiver Two", "RB", 24),
    ]
    for player_id, name, position, age in players:
        db.execute(
            """
            INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
            VALUES (?, ?, ?, 'X', ?, ?)
            """,
            [player_id, name, position, age, json.dumps({"status": "Active"})],
        )
    for row_id, player_id, age_curve, market in [
        (1, "p1", 85 if not distressed else 15, 65),
        (2, "p2", 78 if not distressed else 18, 72),
        (3, "p3", 81 if not distressed else 20, 40),
        (4, "p4", 74, 35),
    ]:
        db.execute(
            """
            INSERT INTO player_values (
                id, league_id, roster_id, player_id,
                comp_current_production, comp_short_term, comp_role_stability,
                comp_age_curve, comp_insulation, comp_market_liquidity,
                comp_positional_scarcity, comp_fragility, comp_ceiling, comp_floor,
                comp_rerollability, comp_contract,
                lens_production, lens_market, lens_insulation, lens_team_fit, lens_direction
            )
            VALUES (?, 'orphan_x', 1, ?, 0, 0, 0, ?, 0, 0, 55, 0, 0, 0, 0, 0, 0, ?, 0, 0, 0)
            """,
            [row_id, player_id, age_curve, market],
        )
    db.execute(
        """
        INSERT INTO player_stats_weekly (player_id, player_name, position, season, week, fantasy_points)
        VALUES
            ('fa1', 'Waiver One', 'WR', 2026, 1, 11.0),
            ('fa2', 'Waiver Two', 'RB', 2026, 1, 9.0)
        """
    )
    db.execute(
        """
        INSERT INTO pick_values (
            id, league_id, pick_owner_roster_id, pick_year, pick_round,
            expected_draft_slot, base_value, timed_value, league_adjusted_value,
            demand_adjusted_value, timing_label, timing_reasoning
        )
        VALUES
            (1, 'orphan_x', 1, 2026, 1, 1.0, 50.0, 50.0, 50.0, ?,'hold_until_rookie_fever','seed'),
            (2, 'orphan_x', 2, 2026, 1, 1.0, 50.0, 50.0, 50.0, 45.0,'hold_until_rookie_fever','seed')
        """,
        [10.0 if distressed else 70.0],
    )
    db.execute(
        """
        INSERT INTO lineup_scores (
            id, league_id, roster_id, total_lineup_score, title_window_label,
            title_window_composite, ceiling_score, stability_score, depth_score, slot_scores_json
        )
        VALUES
            (1, 'orphan_x', 1, ?, 'Window', 0, 0, 0, 0, '[]'),
            (2, 'orphan_x', 2, 60.0, 'Window', 0, 0, 0, 0, '[]')
        """,
        [18.0 if distressed else 65.0],
    )
    suggestions_json = json.dumps(
        [
            {
                "action_type": "cut",
                "primary_player_ids": ["p3"],
                "primary_player_names": ["Player Three"],
                "reasoning": "Free the bench spot.",
                "direction_fit_score": 0.2,
            }
        ]
        if distressed
        else []
    )
    db.execute(
        """
        INSERT INTO hygiene_suggestions (id, league_id, roster_id, suggestions_json)
        VALUES (1, 'orphan_x', 1, ?)
        """,
        [suggestions_json],
    )


def test_age_curve_score(db):
    _seed_orphan_context(db)
    intake = OrphanEngine(db).compute_intake("orphan_x", 1)
    assert intake.age_curve.score > 70


def test_composite_score_range():
    assert 0.0 <= compute_orphan_composite(10, 20, 30, 40, 50) <= 100.0


def test_action_plan_sort_order(db):
    _seed_orphan_context(db, distressed=True)
    plan = OrphanEngine(db).generate_action_plan("orphan_x", 1, "orphan_intake")
    assert len(plan.items) >= 5
    urgencies = [item.urgency for item in plan.items]
    assert urgencies == sorted(urgencies, key=lambda value: {"this_week": 0, "30_days": 1, "offseason": 2}[value])
    assert any(item.category == "add" for item in plan.items)
    assert any(item.category == "drop" for item in plan.items)


def test_waiver_repo_roundtrip(db):
    repo = WaiverRepo(db)
    waiver_response = WaiverRecommendationsResponse(
        league_id="orphan_x",
        roster_id=1,
        waiver_type_label="faab",
        waiver_type_raw=2,
        remaining_faab=75,
        total_faab=100,
        recommendations=[
            WaiverRecommendation(
                player_id="fa1",
                player_name="Waiver One",
                position="WR",
                team="X",
                recommendation_label="faab_bid",
                bid_low=5,
                bid_mid=8,
                bid_high=11,
                urgency="High",
                rationale="Seeded",
                is_immediate_start=True,
            )
        ],
        computed_at="2026-03-28T00:00:00",
    )
    startup_context = StartupContext(
        league_id="orphan_x",
        draft_status="drafting",
        startup_mode_available=True,
        build_template="rebuild",
        direction_label="hard_rebuild",
        build_template_hint="Seeded",
        pick_valuations=[
            StartupPickValuation(
                pick_slot="1.01",
                pick_slot_number=1,
                tier_label="Elite",
                trade_up_recommended=False,
                trade_down_recommended=False,
                trade_reasoning=None,
                pick_value=88.0,
            )
        ],
        computed_at="2026-03-28T00:00:00",
    )
    orphan_intake = OrphanIntake(
        league_id="orphan_x",
        roster_id=1,
        composite_score=44.0,
        composite_label="Rebuilder",
        age_curve=OrphanIntakeDimension(score=50.0, label="Mixed timeline", summary="Seeded"),
        pick_capital=OrphanIntakeDimension(score=40.0, label="Pick deficit", summary="Seeded"),
        dead_spots=OrphanIntakeDimension(score=30.0, label="Dead weight", summary="Seeded"),
        lineup_viability=OrphanIntakeDimension(score=60.0, label="Thin but viable", summary="Seeded"),
        liquidation_options=OrphanIntakeDimension(score=70.0, label="Liquid market", summary="Seeded"),
        computed_at="2026-03-28T00:00:00",
    )
    action_plan = ActionPlan(
        league_id="orphan_x",
        roster_id=1,
        generated_at="2026-03-28T00:00:00",
        plan_type="orphan_intake",
        items=[
            ActionPlanItem(
                priority_rank=1,
                category="add",
                headline="Add Waiver One",
                rationale="Seeded",
                urgency="this_week",
                target_entity_type="player",
                target_entity_ids=["fa1"],
                confidence_label="HIGH",
            )
        ],
        summary="Seeded",
    )

    repo.upsert_waiver_recommendations(waiver_response)
    repo.upsert_startup_context(startup_context)
    repo.upsert_orphan_intake(orphan_intake)
    repo.upsert_action_plan(action_plan)

    assert repo.get_waiver_recommendations("orphan_x", 1) is not None
    assert repo.get_startup_context("orphan_x") is not None
    assert repo.get_orphan_intake("orphan_x", 1) is not None
    assert repo.get_action_plan("orphan_x", 1) is not None
