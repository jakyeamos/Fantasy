from fantasy.trends.models import TrendResult, trend_to_supporting_factor


def _trend(label: str) -> TrendResult:
    return TrendResult(
        player_id="player_1",
        trend_label=label,
        confidence="HIGH",
        delta_magnitude=0.42,
        component_deltas={"comp_short_term": 0.2},
        adp_delta=12.0,
        seasons_compared=2,
        backfilled=False,
    )


def test_trend_factor_shape():
    factor = trend_to_supporting_factor(_trend("will_rise"))

    assert set(factor.keys()) == {"factor_name", "direction", "magnitude", "explanation"}


def test_trend_factor_direction_will_rise():
    factor = trend_to_supporting_factor(_trend("will_rise"))

    assert factor["direction"] == "positive"


def test_trend_factor_direction_will_fall():
    factor = trend_to_supporting_factor(_trend("will_fall"))

    assert factor["direction"] == "negative"


def test_trend_factor_direction_will_maintain():
    factor = trend_to_supporting_factor(_trend("will_maintain"))

    assert factor["direction"] == "neutral"


def test_magnitude_positive():
    factor = trend_to_supporting_factor(_trend("will_fall"))

    assert factor["magnitude"] >= 0
