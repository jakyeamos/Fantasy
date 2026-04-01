from __future__ import annotations

from fantasy.intelligence.models import PlayerValue
from fantasy.recommendation.anti_overreaction import (
    BEARISH_PRODUCTION_FLOOR,
    BULLISH_CEILING_CAP,
    apply_stabilization,
    is_elite,
)


def _player_value(**overrides) -> PlayerValue:
    payload = {
        "league_id": "league_x",
        "roster_id": 1,
        "player_id": "player_x",
        "comp_current_production": 0.35,
        "comp_insulation": 0.75,
        "comp_ceiling": 0.72,
        "comp_floor": 0.58,
        "comp_age_curve": 0.65,
    }
    payload.update(overrides)
    return PlayerValue(**payload)


def test_elite_composite_requires_all_fields() -> None:
    assert is_elite(_player_value()) is True
    assert is_elite(_player_value(comp_floor=0.45)) is False


def test_bearish_dampening_fires_for_elite_low_production_player() -> None:
    value = apply_stabilization(_player_value(comp_current_production=0.22), [])
    assert value.comp_current_production == BEARISH_PRODUCTION_FLOOR


def test_bearish_dampening_bypassed_when_injury_recovery_flag_active() -> None:
    value = apply_stabilization(
        _player_value(comp_current_production=0.22),
        ["injury_recovery"],
    )
    assert value.comp_current_production == 0.22


def test_bullish_dampening_fires_for_low_insulation_high_ceiling() -> None:
    value = apply_stabilization(
        _player_value(
            comp_insulation=0.25,
            comp_ceiling=0.91,
            comp_floor=0.30,
            comp_age_curve=0.35,
        ),
        [],
    )
    assert value.comp_ceiling == BULLISH_CEILING_CAP


def test_non_elite_player_with_moderate_scores_unmodified() -> None:
    value = _player_value(
        comp_current_production=0.52,
        comp_insulation=0.55,
        comp_ceiling=0.62,
        comp_floor=0.46,
        comp_age_curve=0.48,
    )
    stabilized = apply_stabilization(value, [])
    assert stabilized.comp_current_production == 0.52
    assert stabilized.comp_ceiling == 0.62
