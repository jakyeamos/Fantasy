from __future__ import annotations

import json

from fastapi.testclient import TestClient

from fantasy.actions.command_center import CommandCenterEngine
from fantasy.edge_radar.engine import EdgeRadarEngine
from fantasy.main import create_app
from fantasy.routers.deps import get_read_db_conn, get_write_db_conn


def _override_conn(conn):
    def _getter():
        yield conn

    return _getter


def _seed_league(db) -> None:
    db.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions,
            settings_blob, superflex, tep, ppr
        )
        VALUES ('edge_league', 'Edge League', '2026', '{}', '["QB","RB","WR","TE","BN"]', '{}', FALSE, FALSE, 1.0)
        """
    )
    db.execute(
        """
        INSERT INTO rosters (
            id, league_id, roster_id, owner_id, owner_display_name,
            starters, players, reserve, taxi
        )
        VALUES
            (1, 'edge_league', 1, 'me', 'Me', '[]', '["sell_high","sell_low"]', '[]', '[]'),
            (2, 'edge_league', 2, 'them', 'Them', '[]', '["buy_low","buy_high"]', '[]', '[]')
        """
    )


def _seed_player(
    db,
    *,
    player_id: str,
    player_name: str,
    position: str,
    model_value: float,
    market_value: float,
    adp: float,
    age: int = 24,
    team: str = "EDG",
    metadata: dict[str, object] | None = None,
) -> None:
    db.execute(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [player_id, player_name, position, team, age, json.dumps(metadata or {})],
    )
    db.execute(
        """
        INSERT INTO player_values (
            id, league_id, player_id, roster_id, comp_current_production,
            comp_short_term, comp_role_stability, comp_age_curve,
            comp_insulation, comp_market_liquidity, comp_positional_scarcity,
            comp_fragility, comp_ceiling, comp_floor, comp_rerollability,
            comp_contract, lens_production, lens_market, lens_insulation,
            lens_team_fit, lens_direction
        )
        VALUES (
            (SELECT COALESCE(MAX(id), 0) + 1 FROM player_values),
            'edge_league', ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?
        )
        """,
        [
            player_id,
            model_value,
            model_value,
            model_value,
            model_value,
            model_value,
            market_value,
            model_value,
            1.0 - model_value,
            model_value,
            model_value,
            model_value,
            model_value,
            model_value,
            market_value,
            model_value,
            model_value,
            model_value,
        ],
    )
    db.execute(
        """
        INSERT INTO player_adp_baseline (player_id, player_name, position, adp, adp_source)
        VALUES (?, ?, ?, ?, 'test')
        """,
        [player_id, player_name, position, adp],
    )


def test_edge_radar_ranks_by_market_delta_before_modifiers(db):
    _seed_league(db)
    _seed_player(
        db,
        player_id="buy_low",
        player_name="Buy Low",
        position="WR",
        model_value=0.82,
        market_value=0.50,
        adp=90,
    )
    _seed_player(
        db,
        player_id="buy_high",
        player_name="Buy High",
        position="RB",
        model_value=0.93,
        market_value=0.78,
        adp=18,
    )
    _seed_player(
        db,
        player_id="sell_high",
        player_name="Sell High",
        position="WR",
        model_value=0.42,
        market_value=0.77,
        adp=22,
    )
    _seed_player(
        db,
        player_id="sell_low",
        player_name="Sell Low",
        position="TE",
        model_value=0.21,
        market_value=0.37,
        adp=155,
    )

    response = EdgeRadarEngine(db).build()

    assert [item.player_id for item in response.items[:4]] == [
        "sell_high",
        "buy_low",
        "sell_low",
        "buy_high",
    ]
    assert [item.signal_type for item in response.items[:4]] == [
        "sell_high",
        "buy_low",
        "sell_low",
        "buy_high",
    ]
    assert response.items[0].market_delta == -0.35
    assert response.items[1].market_delta == 0.32
    assert response.items[1].action_label == "Buy low"
    assert response.items[3].action_label == "Buy high"


def test_edge_radar_reports_source_health_and_degraded_state(db):
    _seed_league(db)
    _seed_player(
        db,
        player_id="buy_low",
        player_name="Buy Low",
        position="WR",
        model_value=0.82,
        market_value=0.50,
        adp=90,
    )

    response = EdgeRadarEngine(db).build()

    health_by_source = {source.source: source for source in response.source_health}
    assert health_by_source["sleeper"].status == "ready"
    assert health_by_source["fantasycalc"].status == "ready"
    assert health_by_source["manual_imports"].status == "missing"
    assert health_by_source["allowlisted_scrapers"].status == "missing"
    assert response.status == "degraded"
    assert response.degraded_reason


def test_edge_radar_route_filters_by_signal_type(db):
    _seed_league(db)
    _seed_player(
        db,
        player_id="buy_low",
        player_name="Buy Low",
        position="WR",
        model_value=0.82,
        market_value=0.50,
        adp=90,
    )
    _seed_player(
        db,
        player_id="sell_high",
        player_name="Sell High",
        position="WR",
        model_value=0.42,
        market_value=0.77,
        adp=22,
    )

    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(db)
    app.dependency_overrides[get_write_db_conn] = _override_conn(db)
    client = TestClient(app)

    response = client.get("/edge-radar?signal_type=buy_low")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["player_id"] == "buy_low"
    assert payload["items"][0]["source_evidence"]
    assert payload["items"][0]["cta_destination"].startswith("/trades?")


def test_edge_radar_can_include_waiver_pickups_from_cached_boards(db):
    _seed_league(db)
    db.execute(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES ('waiver_add', 'Waiver Add', 'RB', 'EDG', 23, '{}')
        """
    )
    db.execute(
        """
        INSERT INTO player_adp_baseline (player_id, player_name, position, adp, adp_source)
        VALUES ('waiver_add', 'Waiver Add', 'RB', 170, 'test')
        """
    )
    db.execute(
        """
        INSERT INTO waiver_recommendations (
            id, league_id, roster_id, recommendations_json, computed_at
        )
        VALUES (1, 'edge_league', 1, ?, CURRENT_TIMESTAMP)
        """,
        [
            json.dumps(
                {
                    "recommendations": [
                        {
                            "player_id": "waiver_add",
                            "player_name": "Waiver Add",
                            "position": "RB",
                            "recommendation_label": "faab_bid",
                            "bid_low": 4,
                            "bid_high": 8,
                            "urgency": "High",
                            "rationale": "Fresh role opening.",
                            "is_immediate_start": True,
                            "confidence": "HIGH",
                        }
                    ]
                }
            )
        ],
    )

    response = EdgeRadarEngine(db).build(signal_type="waiver_pickup")

    assert response.items
    item = response.items[0]
    assert item.signal_type == "waiver_pickup"
    assert item.acceptable_price == "$4-$8 FAAB"
    assert item.cta_destination == "/league/edge_league/waivers?rosterId=1"


def test_edge_radar_attaches_similarity_evidence_from_system_age_and_outcomes(db):
    _seed_league(db)
    shared_system = {
        "offensive_system": "wide_zone_play_action",
        "head_coach": "Coach A",
        "offensive_coordinator": "OC A",
    }
    _seed_player(
        db,
        player_id="target_wr",
        player_name="Target WR",
        position="WR",
        model_value=0.82,
        market_value=0.50,
        adp=90,
        age=24,
        team="SEA",
        metadata=shared_system,
    )
    _seed_player(
        db,
        player_id="similar_wr",
        player_name="Similar WR",
        position="WR",
        model_value=0.79,
        market_value=0.53,
        adp=92,
        age=25,
        team="SEA",
        metadata=shared_system,
    )
    _seed_player(
        db,
        player_id="different_wr",
        player_name="Different WR",
        position="WR",
        model_value=0.79,
        market_value=0.53,
        adp=92,
        age=31,
        team="CAR",
        metadata={"offensive_system": "spread", "head_coach": "Coach B"},
    )
    db.execute(
        """
        INSERT INTO player_stats_weekly (
            player_id, player_name, position, season, week, fantasy_points, targets
        )
        VALUES
            ('similar_wr', 'Similar WR', 'WR', 2025, 1, 18.0, 9.0),
            ('similar_wr', 'Similar WR', 'WR', 2025, 2, 14.0, 8.0),
            ('different_wr', 'Different WR', 'WR', 2025, 1, 7.0, 4.0)
        """
    )

    item = next(
        candidate
        for candidate in EdgeRadarEngine(db).build().items
        if candidate.player_id == "target_wr"
    )

    assert item.similarity_score >= 0.85
    assert item.similar_player_outcomes
    assert item.similar_player_outcomes[0].player_id == "similar_wr"
    assert "same offensive system" in item.similar_player_outcomes[0].context
    assert "16.0 fantasy points" in item.similar_player_outcomes[0].outcome_summary
    assert any("Similarity: Similar WR" in evidence for evidence in item.source_evidence)


def test_edge_radar_uses_team_context_source_for_system_similarity(db):
    _seed_league(db)
    db.execute(
        """
        INSERT INTO team_context_by_season (
            team, season, head_coach, offensive_coordinator, play_caller,
            offensive_system, pace_label, pass_rate_label, source, notes
        )
        VALUES
            (
                'SEA', 2026, 'Coach A', 'OC A', 'OC A',
                'wide_zone_play_action', 'neutral', 'balanced', 'manual_csv', 'test'
            ),
            (
                'MIA', 2026, 'Coach A', 'OC A', 'OC A',
                'wide_zone_play_action', 'neutral', 'balanced', 'manual_csv', 'test'
            ),
            (
                'CAR', 2026, 'Coach B', 'OC B', 'OC B',
                'spread', 'slow', 'pass_heavy', 'manual_csv', 'test'
            )
        """
    )
    _seed_player(
        db,
        player_id="target_wr",
        player_name="Target WR",
        position="WR",
        model_value=0.82,
        market_value=0.50,
        adp=90,
        age=24,
        team="SEA",
    )
    _seed_player(
        db,
        player_id="similar_wr",
        player_name="Similar WR",
        position="WR",
        model_value=0.79,
        market_value=0.53,
        adp=92,
        age=25,
        team="MIA",
    )
    _seed_player(
        db,
        player_id="different_wr",
        player_name="Different WR",
        position="WR",
        model_value=0.79,
        market_value=0.53,
        adp=92,
        age=25,
        team="CAR",
    )
    db.execute(
        """
        INSERT INTO player_stats_weekly (
            player_id, player_name, position, season, week, fantasy_points, targets
        )
        VALUES
            ('similar_wr', 'Similar WR', 'WR', 2025, 1, 18.0, 9.0),
            ('different_wr', 'Different WR', 'WR', 2025, 1, 7.0, 4.0)
        """
    )

    response = EdgeRadarEngine(db).build()
    item = next(
        candidate for candidate in response.items if candidate.player_id == "target_wr"
    )
    health_by_source = {source.source: source for source in response.source_health}

    assert health_by_source["manual_imports"].status == "ready"
    assert item.similar_player_outcomes[0].player_id == "similar_wr"
    assert "same offensive system" in item.similar_player_outcomes[0].context
    assert "same head coach" in item.similar_player_outcomes[0].context
    assert any(
        "Team context: wide_zone_play_action" in evidence
        for evidence in item.source_evidence
    )


def test_edge_radar_similarity_uses_dense_role_market_and_outcome_comps(db):
    _seed_league(db)
    dense_profile = {
        "target_share": 0.28,
        "air_yard_share": 0.34,
        "route_participation": 0.88,
        "snap_share": 0.79,
        "red_zone_touches": 5,
        "yards_per_route_run": 2.35,
        "explosive_play_rate": 0.13,
        "first_read_target_share": 0.31,
        "slot_rate": 0.52,
        "goal_line_share": 0.09,
        "pass_rate_over_expectation": 0.04,
        "scoring_environment": 0.74,
        "breakout_age": 21.2,
        "yoy_role_growth": 0.16,
        "trade_value_movement": 0.03,
        "roster_rate": 0.88,
        "six_week_value_delta": 0.18,
    }
    _seed_player(
        db,
        player_id="target_wr",
        player_name="Target WR",
        position="WR",
        model_value=0.82,
        market_value=0.50,
        adp=90,
        age=24,
        team="SEA",
        metadata=dense_profile,
    )
    _seed_player(
        db,
        player_id="dense_comp",
        player_name="Dense Comp",
        position="WR",
        model_value=0.80,
        market_value=0.52,
        adp=92,
        age=24,
        team="MIA",
        metadata={
            **dense_profile,
            "target_share": 0.27,
            "route_participation": 0.86,
            "trade_value_movement": 0.04,
            "six_week_value_delta": 0.22,
        },
    )
    _seed_player(
        db,
        player_id="shallow_comp",
        player_name="Shallow Comp",
        position="WR",
        model_value=0.80,
        market_value=0.52,
        adp=92,
        age=24,
        team="SEA",
        metadata={
            "target_share": 0.12,
            "route_participation": 0.45,
            "yards_per_route_run": 0.85,
            "first_read_target_share": 0.08,
            "roster_rate": 0.35,
            "six_week_value_delta": -0.09,
        },
    )
    db.execute(
        """
        INSERT INTO player_stats_weekly (
            player_id, player_name, position, season, week, fantasy_points, targets
        )
        VALUES
            ('dense_comp', 'Dense Comp', 'WR', 2026, 1, 18.0, 9.0),
            ('dense_comp', 'Dense Comp', 'WR', 2026, 2, 20.0, 10.0),
            ('dense_comp', 'Dense Comp', 'WR', 2026, 6, 16.0, 8.0),
            ('dense_comp', 'Dense Comp', 'WR', 2027, 1, 17.0, 8.0),
            ('shallow_comp', 'Shallow Comp', 'WR', 2026, 1, 6.0, 3.0),
            ('shallow_comp', 'Shallow Comp', 'WR', 2026, 2, 7.0, 3.0)
        """
    )

    item = next(
        candidate
        for candidate in EdgeRadarEngine(db).build().items
        if candidate.player_id == "target_wr"
    )

    assert item.similar_player_outcomes[0].player_id == "dense_comp"
    assert "similar usage" in item.similar_player_outcomes[0].context
    assert "similar role quality" in item.similar_player_outcomes[0].context
    assert "similar market behavior" in item.similar_player_outcomes[0].context
    assert "similar career stage" in item.similar_player_outcomes[0].context
    assert "next 4 weeks 19.0 fantasy points" in item.similar_player_outcomes[0].outcome_summary
    assert "next season 17.0 fantasy points" in item.similar_player_outcomes[0].outcome_summary
    assert any("Outcome comps:" in evidence for evidence in item.source_evidence)


def test_command_center_consumes_edge_radar_discoveries_as_actions(db):
    _seed_league(db)
    _seed_player(
        db,
        player_id="buy_low",
        player_name="Buy Low",
        position="WR",
        model_value=0.82,
        market_value=0.50,
        adp=90,
    )

    response = CommandCenterEngine(db).build("edge_league")

    action = next(item for item in response.actions if item.id == "edge:buy_low:edge_league:buy_low")
    assert action.category == "trade"
    assert action.headline == "Buy low: Buy Low"
    assert "market delta is +0.32" in action.recommended_action
    assert action.cta_destination.startswith("/trades?")
