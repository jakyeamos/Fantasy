from __future__ import annotations

import json

from fantasy.intelligence.models import ScorecardInputs
from fantasy.lineup.constants import HYGIENE_MAX_SUGGESTIONS_PER_TYPE
from fantasy.lineup.hygiene_engine import HygieneEngine


def _inputs(
    league_id: str,
    roster_id: int,
    *,
    bench: list[str],
    starters: list[str] | None = None,
    taxi: list[str] | None = None,
    ages: dict[str, int] | None = None,
    games_played: dict[str, int] | None = None,
    adp_ranks: dict[str, float] | None = None,
    positions: dict[str, str] | None = None,
    league_settings: dict[str, object] | None = None,
) -> ScorecardInputs:
    st = starters or ["s1"]
    player_positions = positions or {p: "WR" for p in st + bench}
    return ScorecardInputs(
        league_id=league_id,
        roster_id=roster_id,
        season=2025,
        roster_positions=["QB", "BN", "BN"],
        starters=st,
        bench=bench,
        ir=[],
        taxi=taxi or [],
        player_ages=ages or {p: 23 for p in st + bench},
        player_positions=player_positions,
        weekly_fantasy_pts={},
        player_games_played=games_played or {},
        adp_ranks=adp_ranks or {},
        pick_rows=[],
        correction_overrides={},
        league_settings=league_settings or {},
        position_medians={"WR": 5.0},
    )


def test_cut_leads_with_slot_blocking_copy(db):
    db.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions,
            settings_blob, superflex, tep, ppr
        )
        VALUES ('lh1', 'H', '2025', '{}', '[]', '{}', FALSE, FALSE, 0.0)
        """
    )
    db.execute(
        """
        INSERT INTO rosters (id, league_id, roster_id, owner_id, starters, players, reserve, taxi)
        VALUES (901, 'lh1', 1, 'o', '["s1"]', '["s1","cutme"]', '[]', '[]')
        """
    )
    db.execute(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES ('cutme', 'Cut Me', 'WR', 'X', 27, '{}'), ('s1', 'Starter', 'WR', 'X', 25, '{}')
        """
    )
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
        VALUES (
            90101, 'lh1', 1, 'cutme',
            0,0,0,0,0,0,0,0,0,0,0,0,
            0,0,0,0,0.05
        )
        """
    )
    eng = HygieneEngine(db)
    inp = _inputs("lh1", 1, bench=["cutme"], starters=["s1"])
    all_in = {1: inp}
    res = eng.compute("lh1", 1, inp, "true_contender", all_in)
    assert res.suggestions
    cut = [s for s in res.suggestions if s.action_type == "cut"]
    assert cut
    assert cut[0].reasoning.startswith("Cutting ")
    assert "frees a roster spot" in cut[0].reasoning


def test_max_five_cuts(db):
    db.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions,
            settings_blob, superflex, tep, ppr
        )
        VALUES ('lh2', 'H', '2025', '{}', '[]', '{}', FALSE, FALSE, 0.0)
        """
    )
    starters = ["s1"]
    bench = [f"bp{i}" for i in range(8)]
    for p in bench + starters:
        db.execute(
            """
            INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
            VALUES (?, ?, 'WR', 'X', 25, '{}')
            """,
            [p, p],
        )
    db.execute(
        """
        INSERT INTO rosters (id, league_id, roster_id, owner_id, starters, players, reserve, taxi)
        VALUES (902, 'lh2', 1, 'o', ?, ?, '[]', '[]')
        """,
        [json.dumps(starters), json.dumps(starters + bench)],
    )
    for i, p in enumerate(bench):
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
            VALUES (?, 'lh2', 1, ?, 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0.05)
            """,
            [92000 + i, p],
        )
    eng = HygieneEngine(db)
    inp = _inputs("lh2", 1, bench=bench, starters=["s1"])
    res = eng.compute("lh2", 1, inp, "true_contender", {1: inp})
    cuts = [s for s in res.suggestions if s.action_type == "cut"]
    assert len(cuts) <= HYGIENE_MAX_SUGGESTIONS_PER_TYPE


def test_consolidation_names_counterparty_when_other_roster_has_target(db):
    db.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions,
            settings_blob, superflex, tep, ppr
        )
        VALUES ('lh3', 'H', '2025', '{}', '[]', '{}', FALSE, FALSE, 0.0)
        """
    )
    db.execute(
        """
        INSERT INTO rosters (id, league_id, roster_id, owner_id, owner_display_name, starters, players, reserve, taxi)
        VALUES
            (903, 'lh3', 1, 'a', 'You', '["s1"]', '["s1","b1","b2"]', '[]', '[]'),
            (904, 'lh3', 2, 'b', 'Counterparty', '["star"]', '["star"]', '[]', '[]')
        """
    )
    for pid, name in [
        ("s1", "S"),
        ("b1", "B1"),
        ("b2", "B2"),
        ("star", "Star"),
    ]:
        db.execute(
            """
            INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
            VALUES (?, ?, 'WR', 'X', 25, '{}')
            """,
            [pid, name],
        )
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
        VALUES
            (931, 'lh3', 1, 'b1', 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0.08),
            (932, 'lh3', 1, 'b2', 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0.07),
            (933, 'lh3', 2, 'star', 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0.9)
        """
    )
    eng = HygieneEngine(db)
    inp1 = _inputs("lh3", 1, bench=["b1", "b2"], starters=["s1"])
    inp2 = _inputs("lh3", 2, bench=[], starters=["star"])
    res = eng.compute("lh3", 1, inp1, "true_contender", {1: inp1, 2: inp2})
    cons = [s for s in res.suggestions if s.action_type == "consolidate"]
    assert cons
    assert cons[0].counterparty_name is not None or "Package" in cons[0].reasoning


def test_stash_young_high_ceiling(db):
    db.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions,
            settings_blob, superflex, tep, ppr
        )
        VALUES ('lh4', 'H', '2025', '{}', '[]', '{}', FALSE, FALSE, 0.0)
        """
    )
    db.execute(
        """
        INSERT INTO rosters (id, league_id, roster_id, owner_id, starters, players, reserve, taxi)
        VALUES (905, 'lh4', 1, 'o', '["s1"]', '["s1","young"]', '[]', '[]')
        """
    )
    db.execute(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES ('young', 'Young WR', 'WR', 'X', 22, '{}'), ('s1', 'S', 'WR', 'X', 25, '{}')
        """
    )
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
        VALUES (
            941, 'lh4', 1, 'young',
            0,0,0,0,0,0,0,0,0.5,0,0,0,
            0,0,0,0,0.4
        )
        """
    )
    eng = HygieneEngine(db)
    inp = _inputs(
        "lh4",
        1,
        bench=["young"],
        starters=["s1"],
        ages={"young": 22, "s1": 25},
    )
    res = eng.compute("lh4", 1, inp, "true_contender", {1: inp})
    stash = [s for s in res.suggestions if s.action_type == "stash"]
    assert stash
    assert "young" in stash[0].reasoning.lower() or "Young" in stash[0].reasoning


def test_taxi_empty_without_config(db):
    db.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions,
            settings_blob, superflex, tep, ppr
        )
        VALUES ('lh5', 'H', '2025', '{}', '[]', '{}', FALSE, FALSE, 0.0)
        """
    )
    db.execute(
        """
        INSERT INTO rosters (id, league_id, roster_id, owner_id, starters, players, reserve, taxi)
        VALUES (906, 'lh5', 1, 'o', '["s1"]', '["s1","rook"]', '[]', '[]')
        """
    )
    db.execute(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES ('rook', 'Rook', 'WR', 'X', 22, '{"years_exp":2023}')
        """
    )
    eng = HygieneEngine(db)
    inp = _inputs("lh5", 1, bench=["rook"], starters=["s1"])
    res = eng.compute("lh5", 1, inp, "true_contender", {1: inp})
    taxi = [s for s in res.suggestions if s.action_type == "taxi"]
    assert taxi == []


def test_ordering_consolidate_before_cut(db):
    db.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions,
            settings_blob, superflex, tep, ppr
        )
        VALUES ('lh6', 'H', '2025', '{}', '[]', '{}', FALSE, FALSE, 0.0)
        """
    )
    db.execute(
        """
        INSERT INTO rosters (id, league_id, roster_id, owner_id, starters, players, reserve, taxi)
        VALUES (907, 'lh6', 1, 'o', '["s1"]', '["s1","c1","c2"]', '[]', '[]')
        """
    )
    db.execute(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES ('c1','C1','WR','X',25,'{}'),('c2','C2','WR','X',25,'{}'),('s1','S','WR','X',25,'{}')
        """
    )
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
        VALUES
            (961, 'lh6', 1, 'c1', 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0.05),
            (962, 'lh6', 1, 'c2', 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0.04)
        """
    )
    eng = HygieneEngine(db)
    inp = _inputs("lh6", 1, bench=["c1", "c2"], starters=["s1"])
    res = eng.compute("lh6", 1, inp, "true_contender", {1: inp})
    types = [s.action_type for s in res.suggestions]
    if "consolidate" in types and "cut" in types:
        assert types.index("consolidate") < types.index("cut")


def test_package_builder_import():
    from fantasy.trade.package_builder import PackageBuilder

    assert PackageBuilder is not None


def _seed_consolidation_db(db, *, target_exploitability: float, target_evidence: int, target_low_confidence: bool):
    """Seed minimal data for a 2-roster consolidation scenario."""
    db.execute("""
        INSERT INTO leagues (league_id, name, season, scoring_settings, roster_positions, settings_blob, superflex, tep, ppr)
        VALUES ('lc1', 'C', '2025', '{}', '["QB","BN","BN"]', '{}', FALSE, FALSE, 0.0)
    """)
    db.execute("""
        INSERT INTO rosters (id, league_id, roster_id, owner_id, owner_display_name, starters, players, reserve, taxi)
        VALUES
          (801, 'lc1', 1, 'u1', 'User', '["s1"]', '["s1","b1","b2"]', '[]', '[]'),
          (802, 'lc1', 2, 'u2', 'Target', '["ts1"]', '["ts1"]', '[]', '[]')
    """)
    for pid in ('s1', 'b1', 'b2', 'ts1'):
        db.execute(
            "INSERT INTO players (player_id, full_name, position, team, age, metadata_blob) VALUES (?, ?, 'WR', 'X', 24, '{}')",
            [pid, pid],
        )
    for pid, lens in [('b1', 0.2), ('b2', 0.25), ('s1', 0.8)]:
        db.execute("""
            INSERT INTO player_values (id, league_id, roster_id, player_id,
                comp_current_production, comp_short_term, comp_role_stability,
                comp_age_curve, comp_insulation, comp_market_liquidity,
                comp_positional_scarcity, comp_fragility, comp_ceiling, comp_floor,
                comp_rerollability, comp_contract,
                lens_production, lens_market, lens_insulation, lens_team_fit, lens_direction)
            VALUES (?, 'lc1', 1, ?, 0,0,0,0,0,0,0,0,0,0,0,0, 0,0,0,0,?)
        """, [8000 + hash(pid) % 1000, pid, lens])
    db.execute("""
        INSERT INTO player_values (id, league_id, roster_id, player_id,
            comp_current_production, comp_short_term, comp_role_stability,
            comp_age_curve, comp_insulation, comp_market_liquidity,
            comp_positional_scarcity, comp_fragility, comp_ceiling, comp_floor,
            comp_rerollability, comp_contract,
            lens_production, lens_market, lens_insulation, lens_team_fit, lens_direction)
        VALUES (9001, 'lc1', 2, 'ts1', 0,0,0,0,0,0,0,0,0,0,0,0, 0,0,0,0,0.8)
    """)
    db.execute("""
        INSERT INTO manager_profiles (id, league_id, roster_id, evidence_count, low_confidence,
            exploitability_score, exploitation_primary, exploitation_secondary,
            exploitation_evidence, aggregate_trade_stats, trade_history)
        VALUES (701, 'lc1', 2, ?, ?, ?, NULL, NULL, '{}', '{}', '[]')
    """, [target_evidence, target_low_confidence, target_exploitability])


def test_consolidation_skips_low_exploitability_manager(db):
    _seed_consolidation_db(db, target_exploitability=25.0, target_evidence=15, target_low_confidence=False)
    eng = HygieneEngine(db)
    inp = _inputs('lc1', 1, bench=['b1', 'b2'], starters=['s1'])
    all_inp = {1: inp, 2: _inputs('lc1', 2, bench=[], starters=['ts1'])}
    result = eng.compute('lc1', 1, inp, 'rebuild', all_inp)
    for s in result.consolidate:
        assert s.counterparty_roster_id is None, (
            f"Should not target roster 2 (exploitability=25.0), got counterparty={s.counterparty_roster_id}"
        )
        assert "trade market" not in s.reasoning.lower()


def test_consolidation_skips_low_confidence_manager(db):
    _seed_consolidation_db(db, target_exploitability=70.0, target_evidence=15, target_low_confidence=True)
    eng = HygieneEngine(db)
    inp = _inputs('lc1', 1, bench=['b1', 'b2'], starters=['s1'])
    all_inp = {1: inp, 2: _inputs('lc1', 2, bench=[], starters=['ts1'])}
    result = eng.compute('lc1', 1, inp, 'rebuild', all_inp)
    for s in result.consolidate:
        assert s.counterparty_roster_id is None, (
            f"Should not target low-confidence roster 2, got counterparty={s.counterparty_roster_id}"
        )


def test_consolidation_targets_exploitable_manager(db):
    _seed_consolidation_db(db, target_exploitability=70.0, target_evidence=15, target_low_confidence=False)
    eng = HygieneEngine(db)
    inp = _inputs('lc1', 1, bench=['b1', 'b2'], starters=['s1'])
    all_inp = {1: inp, 2: _inputs('lc1', 2, bench=[], starters=['ts1'])}
    result = eng.compute('lc1', 1, inp, 'rebuild', all_inp)
    targets = [s.counterparty_roster_id for s in result.consolidate if s.counterparty_roster_id is not None]
    assert 2 in targets, f"Should target exploitable roster 2, got {targets}"


def _insert_player(db, player_id: str, *, name: str | None = None, position: str = "WR", age: int = 25):
    db.execute(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES (?, ?, ?, 'X', ?, '{}')
        """,
        [player_id, name or player_id, position, age],
    )


def _insert_player_value(
    db,
    *,
    row_id: int,
    league_id: str,
    roster_id: int,
    player_id: str,
    lens_direction: float,
    comp_ceiling: float = 0.0,
):
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
        VALUES (?, ?, ?, ?, 0,0,0,0,0,0,0,0,?,0,0,0,0,0,0,0,?)
        """,
        [row_id, league_id, roster_id, player_id, comp_ceiling, lens_direction],
    )


def _insert_transaction(db, *, league_id: str, transaction_id: str, adds: dict[str, int] | None = None):
    db.execute(
        """
        INSERT INTO transactions (
            transaction_id, league_id, type, status, roster_ids, adds, drops, draft_picks, waiver_bid, week
        )
        VALUES (?, ?, 'trade', 'complete', '[]', ?, '{}', '[]', 0, 1)
        """,
        [transaction_id, league_id, json.dumps(adds or {})],
    )


def test_hygiene_engine_emits_depth_actions_and_context_metadata(db):
    league_id = "lh7"
    db.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions,
            settings_blob, superflex, tep, ppr
        )
        VALUES (?, 'H', '2025', '{}', '["RB","WR","BN","BN","BN","BN","BN","BN","BN"]', '{}', FALSE, FALSE, 0.0)
        """,
        [league_id],
    )
    db.execute(
        """
        INSERT INTO rosters (id, league_id, roster_id, owner_id, owner_display_name, starters, players, reserve, taxi)
        VALUES
          (971, ?, 1, 'u1', 'User', '["fragile_rb","shop_old"]',
           '["fragile_rb","shop_old","hold1","pack1","pack2","throw1","reroll1","cut1","hand1","stash1"]',
           '[]', '[]'),
          (972, ?, 2, 'u2', 'Target', '["target_star"]', '["target_star"]', '[]', '[]')
        """,
        [league_id, league_id],
    )
    db.execute(
        """
        INSERT INTO manager_profiles (id, league_id, roster_id, evidence_count, low_confidence,
            exploitability_score, exploitation_primary, exploitation_secondary,
            exploitation_evidence, aggregate_trade_stats, trade_history)
        VALUES (97101, ?, 2, 20, FALSE, 70.0, NULL, NULL, '{}', '{}', '[]')
        """,
        [league_id],
    )

    for player_id, position, age in [
        ("fragile_rb", "RB", 26),
        ("shop_old", "WR", 30),
        ("hold1", "WR", 25),
        ("pack1", "WR", 24),
        ("pack2", "WR", 24),
        ("throw1", "WR", 24),
        ("reroll1", "WR", 24),
        ("cut1", "WR", 24),
        ("hand1", "RB", 24),
        ("stash1", "WR", 22),
        ("target_star", "WR", 25),
    ]:
        _insert_player(db, player_id, position=position, age=age)

    for row_id, player_id, lens, ceiling, roster_id in [
        (97110, "fragile_rb", 0.50, 0.20, 1),
        (97111, "shop_old", 0.70, 0.20, 1),
        (97112, "hold1", 0.45, 0.20, 1),
        (97113, "pack1", 0.25, 0.20, 1),
        (97114, "pack2", 0.35, 0.20, 1),
        (97115, "throw1", 0.20, 0.20, 1),
        (97116, "reroll1", 0.08, 0.20, 1),
        (97117, "cut1", 0.02, 0.20, 1),
        (97118, "hand1", 0.30, 0.20, 1),
        (97119, "stash1", 0.40, 0.50, 1),
        (97120, "target_star", 0.90, 0.30, 2),
    ]:
        _insert_player_value(
            db,
            row_id=row_id,
            league_id=league_id,
            roster_id=roster_id,
            player_id=player_id,
            lens_direction=lens,
            comp_ceiling=ceiling,
        )

    _insert_transaction(db, league_id=league_id, transaction_id="txn-shop", adds={"shop_old": 1})

    engine = HygieneEngine(db)
    inputs = _inputs(
        league_id,
        1,
        starters=["fragile_rb", "shop_old"],
        bench=["hold1", "pack1", "pack2", "throw1", "reroll1", "cut1", "hand1", "stash1"],
        ages={
            "fragile_rb": 26,
            "shop_old": 30,
            "hold1": 25,
            "pack1": 24,
            "pack2": 24,
            "throw1": 24,
            "reroll1": 24,
            "cut1": 24,
            "hand1": 24,
            "stash1": 22,
        },
        positions={
            "fragile_rb": "RB",
            "shop_old": "WR",
            "hold1": "WR",
            "pack1": "WR",
            "pack2": "WR",
            "throw1": "WR",
            "reroll1": "WR",
            "cut1": "WR",
            "hand1": "RB",
            "stash1": "WR",
        },
        games_played={"fragile_rb": 5, "shop_old": 4},
        adp_ranks={"shop_old": 45.0},
    )
    counterparty_inputs = _inputs(league_id, 2, starters=["target_star"], bench=[])

    result = engine.compute(
        league_id,
        1,
        inputs,
        "true_contender",
        {1: inputs, 2: counterparty_inputs},
    )

    assert result.suggestions
    assert all(suggestion.timing_rationale for suggestion in result.suggestions)

    package = next(s for s in result.suggestions if s.action_type == "package")
    throw_in = next(s for s in result.suggestions if s.action_type == "throw_in_now")
    hold = next(s for s in result.suggestions if s.action_type == "hold")
    shop = next(s for s in result.suggestions if s.action_type == "shop")

    assert package.packaging_rationale
    assert throw_in.packaging_rationale
    assert hold.packaging_rationale is None
    assert hold.primary_player_ids == ["hold1"]
    assert "hold despite weak market" in hold.reasoning.lower()
    assert all(
        suggestion.action_type != "cut" and suggestion.action_type != "shop"
        for suggestion in result.suggestions
        if suggestion.primary_player_ids == ["hold1"]
    )
    assert any(s.action_type == "handcuff_speculative" for s in result.suggestions)
    assert any(s.action_type == "reroll_into_pick" for s in result.suggestions)
    assert any(s.action_type == "stash" for s in result.suggestions)
    assert "injury_recovery" in shop.player_context_flags
    assert "injury" in shop.reasoning.lower()


def test_hygiene_engine_coverage_guarantee_on_deep_bench(db):
    league_id = "lh8"
    db.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions,
            settings_blob, superflex, tep, ppr
        )
        VALUES (?, 'H', '2025', '{}', '["WR","BN","BN","BN","BN","BN","BN","BN","BN","BN","BN"]', '{}', FALSE, FALSE, 0.0)
        """,
        [league_id],
    )
    bench_players = [f"bench{i}" for i in range(10)]
    db.execute(
        """
        INSERT INTO rosters (id, league_id, roster_id, owner_id, owner_display_name, starters, players, reserve, taxi)
        VALUES
          (981, ?, 1, 'u1', 'User', '["starter_shop"]',
           ?, '[]', '[]'),
          (982, ?, 2, 'u2', 'Target', '["target_star"]', '["target_star"]', '[]', '[]')
        """,
        [
            league_id,
            json.dumps(["starter_shop", *bench_players]),
            league_id,
        ],
    )
    db.execute(
        """
        INSERT INTO manager_profiles (id, league_id, roster_id, evidence_count, low_confidence,
            exploitability_score, exploitation_primary, exploitation_secondary,
            exploitation_evidence, aggregate_trade_stats, trade_history)
        VALUES (98101, ?, 2, 20, FALSE, 70.0, NULL, NULL, '{}', '{}', '[]')
        """,
        [league_id],
    )

    _insert_player(db, "starter_shop", position="WR", age=29)
    _insert_player(db, "target_star", position="WR", age=25)
    _insert_player_value(
        db,
        row_id=98100,
        league_id=league_id,
        roster_id=1,
        player_id="starter_shop",
        lens_direction=0.62,
        comp_ceiling=0.2,
    )
    _insert_player_value(
        db,
        row_id=98200,
        league_id=league_id,
        roster_id=2,
        player_id="target_star",
        lens_direction=0.88,
        comp_ceiling=0.2,
    )
    _insert_transaction(db, league_id=league_id, transaction_id="txn-starter", adds={"starter_shop": 1})

    for index, player_id in enumerate(bench_players, start=1):
        _insert_player(db, player_id, position="WR", age=24)
        _insert_player_value(
            db,
            row_id=98100 + index,
            league_id=league_id,
            roster_id=1,
            player_id=player_id,
            lens_direction=0.02 + (index * 0.03),
            comp_ceiling=0.2,
        )

    engine = HygieneEngine(db)
    inputs = _inputs(
        league_id,
        1,
        starters=["starter_shop"],
        bench=bench_players,
        positions={"starter_shop": "WR", **{player_id: "WR" for player_id in bench_players}},
        ages={"starter_shop": 29, **{player_id: 24 for player_id in bench_players}},
        adp_ranks={"starter_shop": 40.0},
    )
    counterparty_inputs = _inputs(league_id, 2, starters=["target_star"], bench=[])

    result = engine.compute(
        league_id,
        1,
        inputs,
        "retool",
        {1: inputs, 2: counterparty_inputs},
    )

    action_types = {suggestion.action_type for suggestion in result.suggestions}

    assert action_types.intersection({"cut", "reroll_into_pick"})
    assert "shop" in action_types
    assert action_types.intersection({"package", "throw_in_now", "consolidate"})
