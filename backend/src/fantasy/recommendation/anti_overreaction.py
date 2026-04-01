from __future__ import annotations

from fantasy.intelligence.models import PlayerValue


ELITE_INSULATION_THRESHOLD: float = 0.70
ELITE_CEILING_THRESHOLD: float = 0.65
ELITE_FLOOR_THRESHOLD: float = 0.50
ELITE_AGE_CURVE_THRESHOLD: float = 0.50
BEARISH_PRODUCTION_FLOOR: float = 0.40
BULLISH_CEILING_CAP: float = 0.65
LOW_INSULATION_THRESHOLD: float = 0.40
BREAKOUT_CEILING_THRESHOLD: float = 0.80


def is_elite(value: PlayerValue) -> bool:
    return (
        (value.comp_insulation or 0.0) >= ELITE_INSULATION_THRESHOLD
        and (value.comp_ceiling or 0.0) >= ELITE_CEILING_THRESHOLD
        and (value.comp_floor or 0.0) >= ELITE_FLOOR_THRESHOLD
        and (value.comp_age_curve or 0.0) >= ELITE_AGE_CURVE_THRESHOLD
    )


def apply_stabilization(value: PlayerValue, active_flag_types: list[str]) -> PlayerValue:
    if (
        is_elite(value)
        and "injury_recovery" not in active_flag_types
        and "role_compression" not in active_flag_types
        and (value.comp_current_production or 0.0) < BEARISH_PRODUCTION_FLOOR
    ):
        value.comp_current_production = BEARISH_PRODUCTION_FLOOR

    if (
        (value.comp_insulation or 0.0) <= LOW_INSULATION_THRESHOLD
        and (value.comp_ceiling or 0.0) >= BREAKOUT_CEILING_THRESHOLD
    ):
        value.comp_ceiling = BULLISH_CEILING_CAP

    return value


__all__ = [
    "BEARISH_PRODUCTION_FLOOR",
    "BREAKOUT_CEILING_THRESHOLD",
    "BULLISH_CEILING_CAP",
    "ELITE_AGE_CURVE_THRESHOLD",
    "ELITE_CEILING_THRESHOLD",
    "ELITE_FLOOR_THRESHOLD",
    "ELITE_INSULATION_THRESHOLD",
    "LOW_INSULATION_THRESHOLD",
    "apply_stabilization",
    "is_elite",
]
