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
