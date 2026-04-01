from fantasy.intelligence.models import PlayerValue
from fantasy.intelligence.valuation_engine import ValuationEngine
from fantasy.trends.models import TrendResult


def _elite_value() -> PlayerValue:
    return PlayerValue(
        league_id="league_x",
        roster_id=1,
        player_id="elite_player",
        comp_current_production=0.70,
        comp_short_term=0.74,
        comp_role_stability=0.76,
        comp_age_curve=0.78,
        comp_insulation=0.85,
        comp_market_liquidity=0.72,
        comp_positional_scarcity=0.68,
        comp_fragility=0.20,
        comp_ceiling=0.82,
        comp_floor=0.78,
        comp_rerollability=0.22,
        comp_contract=0.74,
    )


def _non_elite_value() -> PlayerValue:
    return PlayerValue(
        league_id="league_x",
        roster_id=1,
        player_id="non_elite_player",
        comp_current_production=0.45,
        comp_short_term=0.42,
        comp_role_stability=0.44,
        comp_age_curve=0.46,
        comp_insulation=0.30,
        comp_market_liquidity=0.35,
        comp_positional_scarcity=0.38,
        comp_fragility=0.45,
        comp_ceiling=0.30,
        comp_floor=0.30,
        comp_rerollability=0.40,
        comp_contract=0.34,
    )


def _trend(label: str, confidence: str) -> TrendResult:
    return TrendResult(
        player_id="elite_player",
        trend_label=label,
        confidence=confidence,
        delta_magnitude=0.35,
        component_deltas={"comp_short_term": -0.2},
        adp_delta=-10.0,
        seasons_compared=2,
        backfilled=False,
    )


def test_elite_player_will_fall_high_confidence(db):
    engine = ValuationEngine(db)
    value = _elite_value()
    baseline = engine._direction_lens(value, "hard_rebuild")
    weakened = engine._direction_lens(value, "hard_rebuild", trend_result=_trend("will_fall", "HIGH"))

    assert baseline > 0
    assert weakened < baseline * 0.40


def test_elite_player_will_fall_low_confidence(db):
    engine = ValuationEngine(db)
    value = _elite_value()
    baseline = engine._direction_lens(value, "hard_rebuild")
    weakened = engine._direction_lens(value, "hard_rebuild", trend_result=_trend("will_fall", "LOW"))

    assert baseline * 0.75 <= weakened <= baseline * 0.95


def test_non_elite_player_no_weakening(db):
    engine = ValuationEngine(db)
    value = _non_elite_value()
    baseline = engine._direction_lens(value, "hard_rebuild")
    weakened = engine._direction_lens(value, "hard_rebuild", trend_result=_trend("will_fall", "HIGH"))

    assert weakened == baseline


def test_will_rise_no_weakening(db):
    engine = ValuationEngine(db)
    value = _elite_value()
    baseline = engine._direction_lens(value, "hard_rebuild")
    weakened = engine._direction_lens(value, "hard_rebuild", trend_result=_trend("will_rise", "HIGH"))

    assert weakened == baseline
