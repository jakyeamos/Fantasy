from fantasy.trade.models import DimensionScore, ThirdPartyTrade, TradeAsset, TradeRequest
from fantasy.trade.trade_engine import TradeEngine


def _request() -> TradeRequest:
    return TradeRequest(
        league_id="league_x",
        user_roster_id=1,
        counterparty_roster_id=2,
        user_sends=[TradeAsset(asset_type="player", player_id="wr1")],
        user_receives=[TradeAsset(asset_type="player", player_id="qb2")],
    )


def test_evaluate_trade(trade_seed_data):
    engine = TradeEngine(trade_seed_data)
    evaluation = engine.evaluate(_request())
    assert evaluation.market_fairness.score >= 0
    assert evaluation.manager_exploit_quality.reasoning
    assert evaluation.trade_balance is not None


def test_trade_balance_discounts_bulk_depth_against_elite_asset(trade_seed_data):
    trade_seed_data.executemany(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES (?, ?, 'WR', 'TST', 24, '{}')
        """,
        [
            ("depth_trade_1", "Depth Trade 1"),
            ("depth_trade_2", "Depth Trade 2"),
            ("depth_trade_3", "Depth Trade 3"),
            ("depth_trade_4", "Depth Trade 4"),
            ("elite_trade_asset", "Elite Trade Asset"),
        ],
    )
    trade_seed_data.executemany(
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
            ?, 'league_x', ?, ?, ?, ?, 0.4, 0.5, ?, ?,
            ?, 0.4, 0.4, 0.4, 0.4, 0.5, ?, ?, ?, ?, ?
        )
        """,
        [
            (
                9101,
                1,
                "depth_trade_1",
                0.35,
                0.35,
                0.35,
                0.35,
                0.35,
                0.35,
                0.25,
                0.35,
                0.35,
                0.35,
            ),
            (
                9102,
                1,
                "depth_trade_2",
                0.35,
                0.35,
                0.35,
                0.35,
                0.35,
                0.35,
                0.25,
                0.35,
                0.35,
                0.35,
            ),
            (
                9103,
                1,
                "depth_trade_3",
                0.35,
                0.35,
                0.35,
                0.35,
                0.35,
                0.35,
                0.25,
                0.35,
                0.35,
                0.35,
            ),
            (
                9104,
                1,
                "depth_trade_4",
                0.35,
                0.35,
                0.35,
                0.35,
                0.35,
                0.35,
                0.25,
                0.35,
                0.35,
                0.35,
            ),
            (
                9105,
                2,
                "elite_trade_asset",
                0.95,
                0.95,
                0.95,
                0.95,
                0.95,
                0.95,
                1.0,
                0.95,
                0.95,
                0.95,
            ),
        ],
    )

    evaluation = TradeEngine(trade_seed_data).evaluate(
        TradeRequest(
            league_id="league_x",
            user_roster_id=1,
            counterparty_roster_id=2,
            user_sends=[
                TradeAsset(asset_type="player", player_id="depth_trade_1"),
                TradeAsset(asset_type="player", player_id="depth_trade_2"),
                TradeAsset(asset_type="player", player_id="depth_trade_3"),
                TradeAsset(asset_type="player", player_id="depth_trade_4"),
            ],
            user_receives=[TradeAsset(asset_type="player", player_id="elite_trade_asset")],
        )
    )

    assert evaluation.trade_balance is not None
    assert evaluation.trade_balance.sent_raw_value == evaluation.trade_balance.received_raw_value
    assert evaluation.trade_balance.sent_adjusted_value < evaluation.trade_balance.received_adjusted_value
    assert evaluation.market_fairness.score > 60
    assert "bench bulk" in evaluation.market_fairness.reasoning


def test_trade_balance_can_diverge_from_equal_consensus_values(trade_seed_data):
    trade_seed_data.executemany(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES (?, ?, ?, 'TST', 24, '{}')
        """,
        [
            ("context_send_qb", "Context Send QB", "QB"),
            ("context_receive_rb", "Context Receive RB", "RB"),
        ],
    )
    trade_seed_data.executemany(
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
            ?, 'league_x', ?, ?, ?, 0.5, 0.5, 0.5, ?, ?,
            ?, 0.4, 0.5, 0.5, 0.5, 0.5, ?, 0.60, ?, ?, ?
        )
        """,
        [
            (
                9201,
                1,
                "context_send_qb",
                0.45,
                0.45,
                0.45,
                0.45,
                0.45,
                0.45,
                0.45,
                0.45,
            ),
            (
                9202,
                2,
                "context_receive_rb",
                0.75,
                0.78,
                0.70,
                0.82,
                0.75,
                0.78,
                0.82,
                0.80,
            ),
        ],
    )

    evaluation = TradeEngine(trade_seed_data).evaluate(
        TradeRequest(
            league_id="league_x",
            user_roster_id=1,
            counterparty_roster_id=2,
            user_sends=[TradeAsset(asset_type="player", player_id="context_send_qb")],
            user_receives=[TradeAsset(asset_type="player", player_id="context_receive_rb")],
        )
    )

    assert evaluation.trade_balance is not None
    assert evaluation.trade_balance.sent_raw_value == evaluation.trade_balance.received_raw_value
    assert evaluation.trade_balance.received_adjusted_value > evaluation.trade_balance.sent_adjusted_value
    assert evaluation.market_fairness.score > 60
    assert "App context differs from consensus" in evaluation.market_fairness.reasoning


def test_similar_market_prices_do_not_claim_players_are_equivalent(trade_seed_data):
    trade_seed_data.execute(
        """
        UPDATE player_values
        SET lens_market = CASE player_id WHEN 'wr1' THEN 0.70 ELSE 0.69 END,
            lens_production = CASE player_id WHEN 'wr1' THEN 0.90 ELSE 0.45 END,
            comp_market_liquidity = CASE player_id WHEN 'wr1' THEN 0.92 ELSE 0.62 END
        WHERE league_id = 'league_x' AND player_id IN ('wr1', 'wr2')
        """
    )

    evaluation = TradeEngine(trade_seed_data).evaluate(
        TradeRequest(
            league_id="league_x",
            user_roster_id=1,
            counterparty_roster_id=2,
            user_sends=[TradeAsset(asset_type="player", player_id="wr1")],
            user_receives=[TradeAsset(asset_type="player", player_id="wr2")],
        )
    )

    assert evaluation.trade_balance is not None
    assert "do not make these players equivalent" in evaluation.market_fairness.reasoning


def test_low_confidence_rebuild_label_yields_to_dominant_scorecard(trade_seed_data):
    trade_seed_data.execute(
        """
        UPDATE team_directions
        SET primary_label = 'soft_rebuild', confidence = 0.315
        WHERE league_id = 'league_x' AND roster_id = 1
        """
    )
    trade_seed_data.execute(
        """
        UPDATE team_scorecards
        SET win_now = CASE roster_id WHEN 1 THEN 1.0 ELSE 0.60 END,
            future_value = CASE roster_id WHEN 1 THEN 1.0 ELSE 0.55 END
        WHERE league_id = 'league_x'
        """
    )

    evaluation = TradeEngine(trade_seed_data).evaluate(_request())

    assert evaluation.direction_fit.confidence == "LOW"
    assert "not authoritative" in evaluation.direction_fit.reasoning
    assert "first in both win-now and future value" in evaluation.direction_fit.reasoning
    assert evaluation.strategic_distinction.verdict == "neutral"
    assert "soft rebuild" not in evaluation.strategic_distinction.headline.lower()
    assert evaluation.recommendation_cards is not None
    assert "lineup" in evaluation.recommendation_cards[0].action


def test_dimension_scores(trade_seed_data):
    engine = TradeEngine(trade_seed_data)
    evaluation = engine.evaluate(_request())
    dimensions = [
        evaluation.market_fairness,
        evaluation.roster_fit,
        evaluation.direction_fit,
        evaluation.timing_quality,
        evaluation.insulation_delta,
        evaluation.liquidity_delta,
        evaluation.manager_exploit_quality,
    ]
    assert len(dimensions) == 7
    for dimension in dimensions:
        assert isinstance(dimension, DimensionScore)
        assert 0.0 <= dimension.score <= 100.0
        assert dimension.confidence in {"HIGH", "MEDIUM", "LOW"}


def test_reroute_paths(trade_seed_data):
    engine = TradeEngine(trade_seed_data)
    evaluation = engine.evaluate(_request())
    assert evaluation.reroutes is None
    assert evaluation.package is None


def test_strategic_distinction_negative(trade_seed_data):
    engine = TradeEngine(trade_seed_data)
    distinction = engine._compute_strategic_distinction(
        DimensionScore(score=50, confidence="HIGH", reasoning=""),
        DimensionScore(score=40, confidence="HIGH", reasoning=""),
        "hard_rebuild",
    )
    assert distinction.verdict == "negative"


def test_strategic_distinction_advancing(trade_seed_data):
    engine = TradeEngine(trade_seed_data)
    distinction = engine._compute_strategic_distinction(
        DimensionScore(score=50, confidence="HIGH", reasoning=""),
        DimensionScore(score=60, confidence="HIGH", reasoning=""),
        "hard_rebuild",
    )
    assert distinction.verdict == "advancing"


def test_strategic_distinction_neutral(trade_seed_data):
    engine = TradeEngine(trade_seed_data)
    distinction = engine._compute_strategic_distinction(
        DimensionScore(score=50, confidence="HIGH", reasoning=""),
        DimensionScore(score=50, confidence="HIGH", reasoning=""),
        "hard_rebuild",
    )
    assert distinction.verdict == "neutral"


def test_no_manager_profile_returns_low_confidence(trade_seed_data):
    trade_seed_data.execute("DELETE FROM manager_profiles WHERE league_id = 'league_x' AND roster_id = 2")
    trade_seed_data.execute(
        "DELETE FROM manager_pitch_angles WHERE league_id = 'league_x' AND roster_id = 2"
    )
    engine = TradeEngine(trade_seed_data)
    evaluation = engine.evaluate(_request())
    assert evaluation.manager_exploit_quality.confidence == "LOW"


def test_multi_team_context_reduces_dimension_confidence(trade_seed_data):
    engine = TradeEngine(trade_seed_data)
    request = _request()
    request.third_party_trades = [
        ThirdPartyTrade(
            roster_id=3,
            sends=[TradeAsset(asset_type="player", player_id="vet1")],
            receives=[TradeAsset(asset_type="pick", pick_year=2026, pick_round=2)],
        )
    ]
    evaluation = engine.evaluate(request)
    assert evaluation.market_fairness.confidence == "MEDIUM"
    assert "Multi-team context:" in evaluation.market_fairness.reasoning
    assert evaluation.third_party_evaluations is not None
    assert evaluation.third_party_evaluations[0].roster_id == 3
    assert 0.0 <= evaluation.third_party_evaluations[0].market_fairness.score <= 100.0
    assert "scored third-party leg" in evaluation.strategic_distinction.explanation


def test_rebuild_pick_proxy_supports_current_labels(trade_seed_data):
    engine = TradeEngine(trade_seed_data)
    pick_asset = TradeAsset(asset_type="pick", pick_year=2026, pick_round=1)
    one_year_punt = engine._build_pick_proxy(pick_asset, "one_year_punt")
    retool = engine._build_pick_proxy(pick_asset, "retool")
    assert one_year_punt["lens_direction"] > retool["lens_direction"]


def test_pick_valuation_fallback_is_exposed_on_trade_evaluation(trade_seed_data, caplog):
    engine = TradeEngine(trade_seed_data)

    def _raise_pick_value(*args, **kwargs):
        raise RuntimeError("draft order rule unavailable")

    engine._repo.get_pick_value = _raise_pick_value

    evaluation = engine.evaluate(
        TradeRequest(
            league_id="league_x",
            user_roster_id=1,
            counterparty_roster_id=2,
            user_sends=[TradeAsset(asset_type="player", player_id="wr1")],
            user_receives=[
                TradeAsset(
                    asset_type="pick",
                    pick_owner_roster_id=2,
                    pick_year=2026,
                    pick_round=1,
                )
            ],
        )
    )

    assert evaluation.degradation_reasons == [
        "pick_valuation_fallback: 2026 round 1 valued with static market table because draft order rule unavailable"
    ]
    assert "static pick fallback" in evaluation.market_fairness.reasoning
    assert any(
        "pick valuation unavailable" in record.message
        for record in caplog.records
    )


def test_roster_fit_rewards_surplus_to_deficit_trade(trade_seed_data):
    trade_seed_data.executemany(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES (?, ?, ?, 'TST', 25, '{}')
        """,
        [
            ("surplus_qb_1", "Surplus QB 1", "QB"),
            ("surplus_qb_2", "Surplus QB 2", "QB"),
            ("surplus_qb_3", "Surplus QB 3", "QB"),
            ("need_rb", "Need RB", "RB"),
            ("target_rb", "Target RB", "RB"),
            ("target_qb", "Target QB", "QB"),
        ],
    )
    trade_seed_data.execute(
        """
        UPDATE rosters
        SET players = '["qb1","surplus_qb_1","surplus_qb_2","surplus_qb_3","wr1","te1"]'
        WHERE league_id = 'league_x' AND roster_id = 1
        """
    )
    trade_seed_data.execute(
        """
        UPDATE rosters
        SET players = '["qb2","target_qb","target_rb","wr2","te2"]'
        WHERE league_id = 'league_x' AND roster_id = 2
        """
    )
    trade_seed_data.executemany(
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
            ?, 'league_x', ?, ?, 0.55, 0.55, 0.5, 0.5, 0.6, 0.6,
            0.55, 0.4, 0.6, 0.5, 0.5, 0.5, 0.55, ?, 0.6, 0.55, 0.55
        )
        """,
        [
            (9001, 1, "surplus_qb_3", 0.58),
            (9002, 2, "target_rb", 0.58),
            (9003, 2, "target_qb", 0.58),
        ],
    )
    engine = TradeEngine(trade_seed_data)

    surplus_to_deficit = engine.evaluate(
        TradeRequest(
            league_id="league_x",
            user_roster_id=1,
            counterparty_roster_id=2,
            user_sends=[TradeAsset(asset_type="player", player_id="surplus_qb_3")],
            user_receives=[TradeAsset(asset_type="player", player_id="target_rb")],
        )
    )
    surplus_to_surplus = engine.evaluate(
        TradeRequest(
            league_id="league_x",
            user_roster_id=1,
            counterparty_roster_id=2,
            user_sends=[TradeAsset(asset_type="player", player_id="surplus_qb_3")],
            user_receives=[TradeAsset(asset_type="player", player_id="target_qb")],
        )
    )

    assert surplus_to_deficit.roster_fit.score > surplus_to_surplus.roster_fit.score + 12


def test_roster_fit_penalizes_sending_elite_scarce_asset_without_overpay(trade_seed_data):
    trade_seed_data.execute(
        """
        UPDATE leagues
        SET tep = TRUE, roster_positions = '["QB","RB","RB","WR","WR","TE","FLEX","SUPER_FLEX","BN","BN"]'
        WHERE league_id = 'league_x'
        """
    )
    trade_seed_data.executemany(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES (?, ?, ?, 'TST', 24, '{}')
        """,
        [
            ("elite_te_trade", "Elite TE Trade", "TE"),
            ("depth_te_trade", "Depth TE Trade", "TE"),
            ("fair_qb_trade", "Fair QB Trade", "QB"),
        ],
    )
    trade_seed_data.execute(
        """
        UPDATE rosters
        SET players = '["qb1","qb2","elite_te_trade","depth_te_trade","wr1","rb1"]'
        WHERE league_id = 'league_x' AND roster_id = 1
        """
    )
    trade_seed_data.execute(
        """
        UPDATE rosters
        SET players = '["fair_qb_trade","wr2","rb2","te2"]'
        WHERE league_id = 'league_x' AND roster_id = 2
        """
    )
    trade_seed_data.executemany(
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
            ?, 'league_x', ?, ?, 0.6, 0.6, 0.5, 0.5, ?, 0.7,
            ?, 0.3, ?, 0.55, 0.45, 0.5, 0.6, ?, 0.7, ?, 0.6
        )
        """,
        [
            (9011, 1, "elite_te_trade", 0.95, 0.92, 0.95, 0.70, 0.92),
            (9012, 1, "depth_te_trade", 0.45, 0.45, 0.40, 0.30, 0.42),
            (9013, 2, "fair_qb_trade", 0.65, 0.55, 0.65, 0.70, 0.60),
        ],
    )

    evaluation = TradeEngine(trade_seed_data).evaluate(
        TradeRequest(
            league_id="league_x",
            user_roster_id=1,
            counterparty_roster_id=2,
            user_sends=[TradeAsset(asset_type="player", player_id="elite_te_trade")],
            user_receives=[TradeAsset(asset_type="player", player_id="fair_qb_trade")],
        )
    )

    assert evaluation.roster_fit.score < 45
    assert "scarce" in evaluation.roster_fit.reasoning.lower()
