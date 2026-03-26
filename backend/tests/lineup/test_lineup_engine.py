from __future__ import annotations

import duckdb

from fantasy.intelligence.models import ScorecardInputs, TeamScorecard
from fantasy.lineup.constants import FADING_WINDOW_THRESHOLD, PEAK_WINDOW_THRESHOLD
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
        player_games_played={},
        adp_ranks={},
        pick_rows=[],
        correction_overrides={},
        league_settings={},
        position_medians=position_medians or {"QB": 5.0, "RB": 5.0, "WR": 5.0, "TE": 5.0},
    )


def test_compute_replacement_level_qb_min_across_rosters():
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
    assert repl == 15.0


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
    assert repl == 9.0


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
