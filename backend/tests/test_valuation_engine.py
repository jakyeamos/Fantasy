from fantasy.intelligence.valuation_engine import ValuationEngine


def test_all_components_present(phase2_seed_data):
    value = ValuationEngine(phase2_seed_data).compute_player("league_x", 1, "wr1", "true_contender")
    for field in [
        "comp_current_production",
        "comp_short_term",
        "comp_role_stability",
        "comp_age_curve",
        "comp_insulation",
        "comp_market_liquidity",
        "comp_positional_scarcity",
        "comp_fragility",
        "comp_ceiling",
        "comp_floor",
        "comp_rerollability",
        "comp_contract",
    ]:
        assert getattr(value, field) is not None


def test_missing_stats_defaults(phase2_seed_data):
    value = ValuationEngine(phase2_seed_data).compute_player("league_x", 1, "rookie1", "hard_rebuild")
    assert value.comp_current_production is not None


def test_ppr_format_adjustment(phase2_seed_data):
    ppr_value = ValuationEngine(phase2_seed_data).compute_player("league_x", 1, "wr1", "true_contender")
    phase2_seed_data.execute("UPDATE leagues SET ppr = 0.0 WHERE league_id = 'league_x'")
    standard_value = ValuationEngine(phase2_seed_data).compute_player("league_x", 1, "wr1", "true_contender")
    assert ppr_value.comp_current_production > standard_value.comp_current_production


def test_superflex_adjustment(phase2_seed_data):
    superflex_value = ValuationEngine(phase2_seed_data).compute_player("league_x", 1, "qb1", "true_contender")
    phase2_seed_data.execute("UPDATE leagues SET superflex = FALSE WHERE league_id = 'league_x'")
    one_qb_value = ValuationEngine(phase2_seed_data).compute_player("league_x", 1, "qb1", "true_contender")
    assert superflex_value.comp_positional_scarcity > one_qb_value.comp_positional_scarcity


def test_elite_tep_te_gets_replacement_gap_scarcity(phase2_seed_data):
    phase2_seed_data.execute(
        "UPDATE leagues SET tep = TRUE, ppr = 0.5 WHERE league_id = 'league_x'"
    )
    phase2_seed_data.executemany(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES (?, ?, 'TE', 'X', 22, '{}')
        """,
        [
            ("elite_te", "Elite TE",),
            ("replacement_te", "Replacement TE",),
        ],
    )
    phase2_seed_data.executemany(
        """
        INSERT INTO player_adp_baseline (player_id, player_name, position, adp, adp_source)
        VALUES (?, ?, 'TE', ?, 'test')
        """,
        [
            ("elite_te", "Elite TE", 24.0),
            ("replacement_te", "Replacement TE", 220.0),
        ],
    )

    elite = ValuationEngine(phase2_seed_data).compute_player(
        "league_x", 1, "elite_te", "true_contender"
    )
    replacement = ValuationEngine(phase2_seed_data).compute_player(
        "league_x", 1, "replacement_te", "true_contender"
    )

    assert elite.comp_positional_scarcity > replacement.comp_positional_scarcity + 0.12
    assert elite.lens_team_fit > replacement.lens_team_fit


def test_thinner_elite_position_gets_higher_tier_cliff_premium(phase2_seed_data):
    phase2_seed_data.execute(
        "UPDATE leagues SET ppr = 0.5, tep = FALSE WHERE league_id = 'league_x'"
    )
    phase2_seed_data.executemany(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES (?, ?, ?, 'X', 24, '{}')
        """,
        [
            ("cliff_rb", "Cliff RB", "RB"),
            ("rb_2", "RB Two", "RB"),
            ("rb_replacement", "RB Replacement", "RB"),
            ("deep_wr", "Deep WR", "WR"),
            ("wr_2", "WR Two", "WR"),
            ("wr_3", "WR Three", "WR"),
            ("wr_4", "WR Four", "WR"),
            ("wr_5", "WR Five", "WR"),
            ("wr_6", "WR Six", "WR"),
            ("wr_7", "WR Seven", "WR"),
            ("wr_replacement", "WR Replacement", "WR"),
        ],
    )
    phase2_seed_data.executemany(
        """
        INSERT INTO player_adp_baseline (player_id, player_name, position, adp, adp_source)
        VALUES (?, ?, ?, ?, 'test')
        """,
        [
            ("cliff_rb", "Cliff RB", "RB", 18.0),
            ("rb_2", "RB Two", "RB", 32.0),
            ("rb_replacement", "RB Replacement", "RB", 170.0),
            ("deep_wr", "Deep WR", "WR", 18.0),
            ("wr_2", "WR Two", "WR", 24.0),
            ("wr_3", "WR Three", "WR", 30.0),
            ("wr_4", "WR Four", "WR", 36.0),
            ("wr_5", "WR Five", "WR", 42.0),
            ("wr_6", "WR Six", "WR", 48.0),
            ("wr_7", "WR Seven", "WR", 54.0),
            ("wr_replacement", "WR Replacement", "WR", 170.0),
        ],
    )

    rb_value = ValuationEngine(phase2_seed_data).compute_player(
        "league_x", 1, "cliff_rb", "true_contender"
    )
    wr_value = ValuationEngine(phase2_seed_data).compute_player(
        "league_x", 1, "deep_wr", "true_contender"
    )

    assert rb_value.comp_positional_scarcity > wr_value.comp_positional_scarcity + 0.05


def test_surplus_qb_roster_reduces_additional_qb_team_fit(phase2_seed_data):
    phase2_seed_data.executemany(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES (?, ?, 'QB', 'X', 25, '{}')
        """,
        [
            ("surplus_qb_a", "Surplus QB A"),
            ("surplus_qb_b", "Surplus QB B"),
            ("surplus_qb_c", "Surplus QB C"),
            ("target_qb_fit", "Target QB Fit"),
        ],
    )
    phase2_seed_data.execute(
        """
        UPDATE rosters
        SET players = '["qb1","surplus_qb_a","surplus_qb_b","surplus_qb_c","rb1","wr1","te1"]'
        WHERE league_id = 'league_x' AND roster_id = 1
        """
    )
    phase2_seed_data.execute(
        """
        UPDATE rosters
        SET players = '["qb2","rb2","wr2","te2"]'
        WHERE league_id = 'league_x' AND roster_id = 2
        """
    )

    surplus_fit = ValuationEngine(phase2_seed_data).compute_player(
        "league_x", 1, "target_qb_fit", "true_contender"
    )
    thin_fit = ValuationEngine(phase2_seed_data).compute_player(
        "league_x", 2, "target_qb_fit", "true_contender"
    )

    assert thin_fit.lens_team_fit > surplus_fit.lens_team_fit + 0.08


def test_direction_reweight(phase2_seed_data):
    rebuild_value = ValuationEngine(phase2_seed_data).compute_player("league_x", 1, "rookie1", "hard_rebuild")
    contender_value = ValuationEngine(phase2_seed_data).compute_player("league_x", 1, "rookie1", "true_contender")
    assert rebuild_value.lens_direction > contender_value.lens_direction


def test_five_lenses(phase2_seed_data):
    value = ValuationEngine(phase2_seed_data).compute_player("league_x", 1, "wr1", "productive_struggle")
    for field in [
        "lens_production",
        "lens_market",
        "lens_insulation",
        "lens_team_fit",
        "lens_direction",
    ]:
        assert getattr(value, field) is not None


def test_compute_player_writes_player_trend_row(phase2_seed_data):
    engine = ValuationEngine(phase2_seed_data)

    engine.compute_player("league_x", 1, "wr1", "true_contender")

    row = phase2_seed_data.execute(
        """
        SELECT player_id, season, startup_adp
        FROM player_trends
        WHERE player_id = 'wr1'
        LIMIT 1
        """
    ).fetchone()
    assert row == ("wr1", 2025, 10.0)
