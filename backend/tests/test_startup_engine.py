from __future__ import annotations

from fantasy.waiver.startup_engine import (
    assign_build_template,
    detect_startup_mode,
    evaluate_pick_recommendations,
)


def test_startup_detection():
    assert detect_startup_mode("pre_draft") is True
    assert detect_startup_mode("drafting") is True
    assert detect_startup_mode("complete") is False


def test_build_template_assignment():
    assert assign_build_template("true_contender") == "win_now"
    assert assign_build_template("hard_rebuild") == "rebuild"
    assert assign_build_template("fringe_playoff") == "balanced"


def test_trade_up_trigger():
    trade_up, trade_down, reasoning = evaluate_pick_recommendations(
        current_score=55.0,
        next_tier_score=80.0,
        slots_to_next_tier_break=1,
        same_tier_remaining_in_draft=1,
    )
    assert trade_up is True
    assert trade_down is False
    assert reasoning is not None


def test_trade_down_trigger():
    trade_up, trade_down, reasoning = evaluate_pick_recommendations(
        current_score=62.0,
        next_tier_score=None,
        slots_to_next_tier_break=None,
        same_tier_remaining_in_draft=3,
    )
    assert trade_up is False
    assert trade_down is True
    assert reasoning is not None
