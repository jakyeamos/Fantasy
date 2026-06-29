from __future__ import annotations

import duckdb

from fantasy.intelligence.models import ScorecardInputs, TeamScorecard
from fantasy.lineup.constants import (
    ELITE_INSULATION_THRESHOLD,
    FADING_WINDOW_THRESHOLD,
    PEAK_WINDOW_THRESHOLD,
    TE_NON_PREMIUM_URGENCY_WEIGHT,
)
from fantasy.lineup.lineup_engine import LineupEngine


def _base_inputs(
    roster_id: int,
    *,
    roster_positions: list[str],
    starters: list[str],
    bench: list[str],
    weekly: dict[str, float] | None = None,
    position_medians: dict[str, float] | None = None,
    player_positions: dict[str, str] | None = None,
    player_ages: dict[str, int] | None = None,
    player_games_played: dict[str, int] | None = None,
    league_settings: dict[str, object] | None = None,
) -> ScorecardInputs:
    pos = player_positions or {p: "QB" for p in starters}
    ages = player_ages or {p: 24 for p in starters + bench}
    return ScorecardInputs(
        league_id="league_t",
        roster_id=roster_id,
        season=2025,
        roster_positions=roster_positions,
        starters=starters,
        bench=bench,
        ir=[],
        taxi=[],
        player_ages=ages,
        player_positions=pos,
        weekly_fantasy_pts=weekly or {},
        player_games_played=player_games_played or {},
        adp_ranks={},
        pick_rows=[],
        correction_overrides={},
        league_settings=league_settings or {},
        position_medians=position_medians or {"QB": 5.0, "RB": 5.0, "WR": 5.0, "TE": 5.0},
    )


def _scorecard(
    league_id: str,
    roster_id: int,
    *,
    fragility: float,
    positional_insulation: float,
    future_value: float = 0.5,
    pick_capital: float = 0.5,
    age_risk: float = 0.5,
) -> TeamScorecard:
    return TeamScorecard(
        league_id=league_id,
        roster_id=roster_id,
        win_now=0.5,
        future_value=future_value,
        depth=0.5,
        pick_capital=pick_capital,
        flexibility=0.5,
        fragility=fragility,
        age_risk=age_risk,
        liquidity=0.5,
        positional_insulation=positional_insulation,
        composite=0.5,
    )


def test_compute_replacement_level_qb_uses_median_across_rosters():
    conn = duckdb.connect(":memory:")
    eng = LineupEngine(conn)
    all_in = {
        1: _base_inputs(
            1,
            roster_positions=["QB", "BN"],
            starters=["q1"],
            bench=[],
            weekly={"q1": 20.0},
        ),
        2: _base_inputs(
            2,
            roster_positions=["QB", "BN"],
            starters=["q2"],
            bench=[],
            weekly={"q2": 18.0},
        ),
        3: _base_inputs(
            3,
            roster_positions=["QB", "BN"],
            starters=["q3"],
            bench=[],
            weekly={"q3": 15.0},
        ),
    }
    repl = eng._compute_replacement_level(all_in, "QB", flex_pool=False)
    assert repl == 18.0


def test_compute_replacement_level_falls_back_to_median_when_no_starters():
    conn = duckdb.connect(":memory:")
    eng = LineupEngine(conn)
    all_in = {
        1: _base_inputs(
            1,
            roster_positions=["QB", "BN"],
            starters=["q1"],
            bench=[],
            weekly={"q1": 20.0},
            position_medians={"QB": 7.5, "RB": 5.0},
        ),
    }
    repl = eng._compute_replacement_level(all_in, "RB", flex_pool=False)
    assert repl == 5.0


def test_flex_replacement_uses_flex_pool():
    conn = duckdb.connect(":memory:")
    eng = LineupEngine(conn)
    all_in = {
        1: _base_inputs(
            1,
            roster_positions=["SUPER_FLEX", "BN"],
            starters=["x1"],
            bench=[],
            weekly={"x1": 12.0},
            player_positions={"x1": "WR"},
        ),
        2: _base_inputs(
            2,
            roster_positions=["SUPER_FLEX", "BN"],
            starters=["x2"],
            bench=[],
            weekly={"x2": 9.0},
            player_positions={"x2": "WR"},
        ),
    }
    repl = eng._compute_replacement_level(all_in, "", flex_pool=True)
    assert repl == 10.5


def test_compute_all_three_team_league_has_slot_scores():
    conn = duckdb.connect(":memory:")
    eng = LineupEngine(conn)
    all_in = {
        1: _base_inputs(
            1,
            roster_positions=["QB", "BN"],
            starters=["q1"],
            bench=[],
            weekly={"q1": 22.0},
        ),
        2: _base_inputs(
            2,
            roster_positions=["QB", "BN"],
            starters=["q2"],
            bench=[],
            weekly={"q2": 20.0},
        ),
        3: _base_inputs(
            3,
            roster_positions=["QB", "BN"],
            starters=["q3"],
            bench=[],
            weekly={"q3": 18.0},
        ),
    }
    out = eng.compute_all("league_t", all_in, scorecards=None)
    assert len(out) == 3
    for rid in (1, 2, 3):
        assert len(out[rid].slot_scores) == 1
        assert out[rid].slot_scores[0].position == "QB"


def test_compute_all_builds_full_lineup_from_starters_plus_bench():
    conn = duckdb.connect(":memory:")
    eng = LineupEngine(conn)
    all_in = {
        1: _base_inputs(
            1,
            roster_positions=["QB", "RB", "WR", "FLEX", "BN", "BN", "BN"],
            starters=["q1", "r1"],
            bench=["w1", "w2", "r2"],
            weekly={"q1": 24.0, "r1": 18.0, "w1": 17.0, "w2": 14.0, "r2": 12.0},
            player_positions={
                "q1": "QB",
                "r1": "RB",
                "w1": "WR",
                "w2": "WR",
                "r2": "RB",
            },
        ),
        2: _base_inputs(
            2,
            roster_positions=["QB", "RB", "WR", "FLEX", "BN", "BN", "BN"],
            starters=["q2", "r3", "w3", "r4"],
            bench=["w4"],
            weekly={"q2": 16.0, "r3": 12.0, "w3": 11.0, "r4": 9.0, "w4": 7.0},
            player_positions={
                "q2": "QB",
                "r3": "RB",
                "w3": "WR",
                "r4": "RB",
                "w4": "WR",
            },
        ),
    }

    out = eng.compute_all("league_t", all_in, scorecards=None)
    roster_one_slots = out[1].slot_scores

    assert len(roster_one_slots) == 4
    assert {slot.player_id for slot in roster_one_slots} == {"q1", "r1", "w1", "w2"}
    assert out[1].total_lineup_score > out[2].total_lineup_score


def test_compute_all_preserves_submitted_starters_over_higher_bench_values():
    conn = duckdb.connect(":memory:")
    eng = LineupEngine(conn)
    all_in = {
        1: _base_inputs(
            1,
            roster_positions=["QB", "WR", "BN"],
            starters=["starter_qb", "starter_wr"],
            bench=["bench_wr"],
            weekly={"starter_qb": 18.0, "starter_wr": 9.0, "bench_wr": 20.0},
            player_positions={
                "starter_qb": "QB",
                "starter_wr": "WR",
                "bench_wr": "WR",
            },
        ),
        2: _base_inputs(
            2,
            roster_positions=["QB", "WR", "BN"],
            starters=["other_qb", "other_wr"],
            bench=[],
            weekly={"other_qb": 16.0, "other_wr": 8.0},
            player_positions={
                "other_qb": "QB",
                "other_wr": "WR",
            },
        ),
    }

    result = eng.compute_all("league_t", all_in, scorecards=None)[1]

    assert {slot.player_id for slot in result.slot_scores} == {"starter_qb", "starter_wr"}
    assert "bench_wr" not in {slot.player_id for slot in result.slot_scores}


def test_title_window_peak_fading_outside():
    conn = duckdb.connect(":memory:")
    eng = LineupEngine(conn)
    # Two rosters — spread ceiling via weekly pts on single QB slot
    all_in = {
        1: _base_inputs(
            1,
            roster_positions=["QB", "BN"],
            starters=["a"],
            bench=["b1", "b2"],
            weekly={"a": 40.0, "b1": 15.0, "b2": 14.0},
        ),
        2: _base_inputs(
            2,
            roster_positions=["QB", "BN"],
            starters=["c"],
            bench=["d1"],
            weekly={"c": 5.0, "d1": 4.0},
        ),
    }
    sc = {
        1: TeamScorecard(
            league_id="league_t",
            roster_id=1,
            win_now=0.5,
            future_value=0.5,
            depth=0.5,
            pick_capital=0.5,
            flexibility=0.5,
            fragility=0.0,
            age_risk=0.5,
            liquidity=0.5,
            positional_insulation=0.5,
            composite=0.5,
        ),
        2: TeamScorecard(
            league_id="league_t",
            roster_id=2,
            win_now=0.5,
            future_value=0.5,
            depth=0.5,
            pick_capital=0.5,
            flexibility=0.5,
            fragility=0.9,
            age_risk=0.5,
            liquidity=0.5,
            positional_insulation=0.5,
            composite=0.5,
        ),
    }
    out = eng.compute_all("league_t", all_in, scorecards=sc)
    hi = out[1]
    lo = out[2]
    assert hi.title_window_composite >= PEAK_WINDOW_THRESHOLD or hi.title_window_label in (
        "Peak Window",
        "Fading Window",
    )
    assert lo.title_window_composite < hi.title_window_composite
    assert lo.title_window_label in ("Fading Window", "Outside Window")


def test_league_normalization_ceiling_spread():
    conn = duckdb.connect(":memory:")
    eng = LineupEngine(conn)
    all_in = {
        1: _base_inputs(
            1,
            roster_positions=["QB", "BN"],
            starters=["a"],
            bench=[],
            weekly={"a": 100.0},
        ),
        2: _base_inputs(
            2,
            roster_positions=["QB", "BN"],
            starters=["b"],
            bench=[],
            weekly={"b": 0.0},
        ),
    }
    out = eng.compute_all("league_t", all_in, scorecards=None)
    assert out[1].ceiling_score >= out[2].ceiling_score
    assert abs(out[1].ceiling_score - 1.0) < 0.01 or out[1].ceiling_score > out[2].ceiling_score


def test_title_window_threshold_constants():
    assert PEAK_WINDOW_THRESHOLD == 0.65
    assert FADING_WINDOW_THRESHOLD == 0.35


def test_title_window_target_attainment_with_future_insulation_is_peak():
    conn = duckdb.connect(":memory:")
    eng = LineupEngine(conn)
    all_in = {
        1: _base_inputs(
            1,
            roster_positions=["QB", "WR", "RB", "BN", "BN"],
            starters=["qb1", "wr1", "rb1"],
            bench=["b1", "b2"],
            weekly={"qb1": 26.0, "wr1": 22.0, "rb1": 20.0, "b1": 7.0, "b2": 6.0},
            player_positions={
                "qb1": "QB",
                "wr1": "WR",
                "rb1": "RB",
                "b1": "WR",
                "b2": "RB",
            },
        ),
        2: _base_inputs(
            2,
            roster_positions=["QB", "WR", "RB", "BN", "BN"],
            starters=["qb2", "wr2", "rb2"],
            bench=["b3", "b4"],
            weekly={"qb2": 28.0, "wr2": 14.0, "rb2": 12.0, "b3": 8.0, "b4": 7.0},
            player_positions={
                "qb2": "QB",
                "wr2": "WR",
                "rb2": "RB",
                "b3": "WR",
                "b4": "RB",
            },
        ),
        3: _base_inputs(
            3,
            roster_positions=["QB", "WR", "RB", "BN", "BN"],
            starters=["qb3", "wr3", "rb3"],
            bench=["b5", "b6"],
            weekly={"qb3": 18.0, "wr3": 12.0, "rb3": 10.0, "b5": 9.0, "b6": 8.0},
            player_positions={
                "qb3": "QB",
                "wr3": "WR",
                "rb3": "RB",
                "b5": "WR",
                "b6": "RB",
            },
        ),
    }
    scorecards = {
        1: _scorecard(
            "league_t",
            1,
            fragility=0.65,
            positional_insulation=0.5,
            future_value=1.0,
            pick_capital=1.0,
            age_risk=0.2,
        ),
        2: _scorecard("league_t", 2, fragility=0.0, positional_insulation=0.5),
        3: _scorecard("league_t", 3, fragility=0.2, positional_insulation=0.5),
    }

    result = eng.compute_all("league_t", all_in, scorecards)[1]

    assert result.overall_gap_to_title_target == 0.0
    assert result.title_window_composite < PEAK_WINDOW_THRESHOLD
    assert result.title_window_label == "Peak Window"


def test_slot_score_position_uses_player_position_not_slot_label():
    conn = duckdb.connect(":memory:")
    eng = LineupEngine(conn)
    # Purdy (QB) in SUPER_FLEX slot — should show "QB", not "SUPER_FLEX"
    all_in = {
        1: _base_inputs(
            1,
            roster_positions=["SUPER_FLEX", "BN"],
            starters=["qb1"],
            bench=[],
            weekly={"qb1": 22.0},
            player_positions={"qb1": "QB"},
        ),
        2: _base_inputs(
            2,
            roster_positions=["SUPER_FLEX", "BN"],
            starters=["qb2"],
            bench=[],
            weekly={"qb2": 18.0},
            player_positions={"qb2": "QB"},
        ),
    }
    results = eng.compute_all("league_t", all_in)
    slot = results[1].slot_scores[0]
    assert slot.position == "QB", f"expected QB, got {slot.position!r}"


def test_lineup_strength_2_contender_benchmark_and_upgrade_leverage():
    conn = duckdb.connect(":memory:")
    eng = LineupEngine(conn)
    all_in = {
        roster_id: _base_inputs(
            roster_id,
            roster_positions=["QB", "BN"],
            starters=[f"q{roster_id}"],
            bench=[],
            weekly={f"q{roster_id}": weekly},
            player_positions={f"q{roster_id}": "QB"},
        )
        for roster_id, weekly in {
            1: 30.0,
            2: 28.0,
            3: 20.0,
            4: 18.0,
            5: 16.0,
            6: 14.0,
        }.items()
    }
    scorecards = {
        roster_id: _scorecard(
            "league_t",
            roster_id,
            fragility=0.2,
            positional_insulation=0.2,
        )
        for roster_id in all_in
    }

    results = eng.compute_all("league_t", all_in, scorecards)

    contender_slot = results[3].slot_scores[0]
    low_slot = results[6].slot_scores[0]

    assert results[3].contender_benchmark_used is True
    assert contender_slot.benchmark_used is True
    assert contender_slot.benchmark_source == "benchmark_pool"
    assert contender_slot.playoff_target >= contender_slot.replacement_level
    assert contender_slot.title_target >= contender_slot.playoff_target
    assert contender_slot.elite_target >= contender_slot.title_target
    assert contender_slot.contender_benchmark == contender_slot.title_target
    assert results[3].overall_playoff_target >= results[3].total_lineup_score
    assert results[3].overall_title_target >= results[3].overall_playoff_target
    assert results[3].overall_elite_target >= results[3].overall_title_target
    assert results[3].overall_gap_to_title_target > 0.0
    assert contender_slot.gap_to_playoff_target > 0.0
    assert contender_slot.gap_to_title_target == contender_slot.upgrade_leverage_score
    assert contender_slot.gap_to_elite_target >= contender_slot.gap_to_title_target
    assert contender_slot.weak_by_median is False
    assert contender_slot.below_playoff_target is True
    assert contender_slot.below_title_target is True
    assert contender_slot.below_elite_target is True
    assert contender_slot.weak_relative_to_contender is True
    assert results[3].upgrade_leverage_point == "q3 (QB)"
    assert 0.0 < results[3].upgrade_title_equity_delta <= 1.0
    assert low_slot.weak_by_median is True
    assert low_slot.below_playoff_target is True
    assert low_slot.weak_relative_to_contender is True


def test_lineup_strength_uses_tier_targets_in_small_leagues():
    conn = duckdb.connect(":memory:")
    eng = LineupEngine(conn)
    all_in = {
        roster_id: _base_inputs(
            roster_id,
            roster_positions=["QB", "BN"],
            starters=[f"q{roster_id}"],
            bench=[],
            weekly={f"q{roster_id}": weekly},
            player_positions={f"q{roster_id}": "QB"},
        )
        for roster_id, weekly in {
            1: 30.0,
            2: 20.0,
            3: 14.0,
        }.items()
    }
    scorecards = {
        roster_id: _scorecard(
            "league_t",
            roster_id,
            fragility=0.2,
            positional_insulation=0.2,
        )
        for roster_id in all_in
    }

    results = eng.compute_all("league_t", all_in, scorecards)

    weak_slot = results[3].slot_scores[0]

    assert results[3].contender_benchmark_used is True
    assert weak_slot.benchmark_source in {"benchmark_pool", "top_tier_fallback"}
    assert weak_slot.playoff_target > weak_slot.replacement_level
    assert weak_slot.title_target >= weak_slot.playoff_target
    assert weak_slot.weak_relative_to_contender is True


def test_elite_insulation_guard_te_weight_and_context_flags():
    conn = duckdb.connect(":memory:")
    eng = LineupEngine(conn)
    all_in = {
        roster_id: _base_inputs(
            roster_id,
            roster_positions=["TE", "BN"],
            starters=[f"te{roster_id}"],
            bench=[],
            weekly={f"te{roster_id}": weekly},
            player_positions={f"te{roster_id}": "TE"},
            player_ages={f"te{roster_id}": age},
            player_games_played={f"te{roster_id}": games},
            league_settings={"te_premium": te_premium},
        )
        for roster_id, weekly, age, games, te_premium in [
            (1, 16.0, 27, 16, True),
            (2, 15.0, 32, 5, False),
            (3, 12.0, 27, 16, False),
            (4, 11.0, 27, 16, False),
            (5, 10.0, 27, 16, False),
            (6, 9.0, 27, 16, False),
        ]
    }
    scorecards = {
        1: _scorecard("league_t", 1, fragility=0.1, positional_insulation=0.2),
        2: _scorecard(
            "league_t",
            2,
            fragility=0.1,
            positional_insulation=ELITE_INSULATION_THRESHOLD + 0.05,
        ),
        3: _scorecard("league_t", 3, fragility=0.1, positional_insulation=0.2),
        4: _scorecard("league_t", 4, fragility=0.1, positional_insulation=0.2),
        5: _scorecard("league_t", 5, fragility=0.1, positional_insulation=0.2),
        6: _scorecard("league_t", 6, fragility=0.1, positional_insulation=0.2),
    }

    results = eng.compute_all("league_t", all_in, scorecards)

    premium_slot = results[1].slot_scores[0]
    guarded_slot = results[2].slot_scores[0]

    assert premium_slot.format_urgency_weight == 1.0
    assert guarded_slot.format_urgency_weight == TE_NON_PREMIUM_URGENCY_WEIGHT
    assert guarded_slot.elite_insulation_guard is True
    assert guarded_slot.upgrade_leverage_score == guarded_slot.gap_to_title_target
    assert guarded_slot.gap_to_title_target >= guarded_slot.gap_to_playoff_target
    assert guarded_slot.gap_to_elite_target >= guarded_slot.gap_to_title_target
    assert "age_cliff_proximity" in guarded_slot.player_context_flags
    assert "injury_recovery" in guarded_slot.player_context_flags


def test_lineup_strength_uses_current_strength_snapshot_not_raw_ppg_only():
    conn = duckdb.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE player_stats_weekly (
            player_id VARCHAR,
            fantasy_points DOUBLE
        )
        """
    )
    conn.execute(
        """
        INSERT INTO player_stats_weekly (player_id, fantasy_points)
        VALUES
            ('elite_wr', 28.0),
            ('elite_wr', 25.0),
            ('steady_wr', 18.0),
            ('steady_wr', 15.0)
        """
    )

    eng = LineupEngine(conn)
    all_in = {
        1: _base_inputs(
            1,
            roster_positions=["WR", "BN"],
            starters=["elite_wr"],
            bench=[],
            weekly={"elite_wr": 12.0},
            player_positions={"elite_wr": "WR"},
            player_games_played={"elite_wr": 12},
        ),
        2: _base_inputs(
            2,
            roster_positions=["WR", "BN"],
            starters=["steady_wr"],
            bench=[],
            weekly={"steady_wr": 13.0},
            player_positions={"steady_wr": "WR"},
            player_games_played={"steady_wr": 17},
        ),
    }

    results = eng.compute_all("league_t", all_in, scorecards=None)

    elite_slot = results[1].slot_scores[0]
    steady_slot = results[2].slot_scores[0]

    assert elite_slot.starter_value > 12.0
    assert elite_slot.starter_value > steady_slot.starter_value
