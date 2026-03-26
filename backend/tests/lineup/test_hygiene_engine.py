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
) -> ScorecardInputs:
    st = starters or ["s1"]
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
        player_positions={p: "WR" for p in st + bench},
        weekly_fantasy_pts={},
        player_games_played={},
        adp_ranks={},
        pick_rows=[],
        correction_overrides={},
        league_settings={},
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
