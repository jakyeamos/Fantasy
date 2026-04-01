from fantasy.trends.constants import COMPONENT_COLS
from fantasy.trends.trend_engine import TrendEngine
from fantasy.trends.trend_repo import TrendRepo


def _components(score: float, *, fragility: float | None = None) -> dict[str, float]:
    values = {column: score for column in COMPONENT_COLS}
    values["comp_fragility"] = fragility if fragility is not None else max(0.0, min(1.0, 1.0 - score))
    return values


def _insert_trend_row(
    conn,
    *,
    player_id: str,
    season: int,
    score: float,
    startup_adp: float,
    backfilled: bool = False,
) -> None:
    TrendRepo(conn).write_trend_row(
        player_id=player_id,
        season=season,
        trend_label=None,
        confidence=None,
        delta_magnitude=0.0,
        adp_delta=None,
        components=_components(score),
        startup_adp=startup_adp,
        backfilled=backfilled,
    )


def test_trend_engine_will_rise(phase2_seed_data):
    _insert_trend_row(phase2_seed_data, player_id="wr1", season=2023, score=0.30, startup_adp=42.0)
    _insert_trend_row(phase2_seed_data, player_id="wr1", season=2024, score=0.82, startup_adp=18.0)

    result = TrendEngine(phase2_seed_data).compute_trend("wr1")

    assert result.trend_label == "will_rise"


def test_trend_engine_will_fall(phase2_seed_data):
    _insert_trend_row(phase2_seed_data, player_id="vet1", season=2023, score=0.84, startup_adp=36.0)
    _insert_trend_row(phase2_seed_data, player_id="vet1", season=2024, score=0.28, startup_adp=92.0)

    result = TrendEngine(phase2_seed_data).compute_trend("vet1")

    assert result.trend_label == "will_fall"


def test_trend_engine_will_maintain(phase2_seed_data):
    _insert_trend_row(phase2_seed_data, player_id="qb1", season=2023, score=0.58, startup_adp=35.0)
    _insert_trend_row(phase2_seed_data, player_id="qb1", season=2024, score=0.61, startup_adp=33.0)

    result = TrendEngine(phase2_seed_data).compute_trend("qb1")

    assert result.trend_label == "will_maintain"


def test_trend_confidence_high(phase2_seed_data):
    _insert_trend_row(phase2_seed_data, player_id="rb1", season=2023, score=0.35, startup_adp=48.0)
    _insert_trend_row(phase2_seed_data, player_id="rb1", season=2024, score=0.82, startup_adp=22.0)

    result = TrendEngine(phase2_seed_data).compute_trend("rb1")

    assert result.confidence == "HIGH"


def test_trend_confidence_low(phase2_seed_data):
    _insert_trend_row(
        phase2_seed_data,
        player_id="te1",
        season=2023,
        score=0.40,
        startup_adp=80.0,
        backfilled=True,
    )
    _insert_trend_row(phase2_seed_data, player_id="te1", season=2024, score=0.75, startup_adp=44.0)

    result = TrendEngine(phase2_seed_data).compute_trend("te1")

    assert result.confidence == "LOW"


def test_trend_backfill_proxy(phase2_seed_data):
    _insert_trend_row(phase2_seed_data, player_id="rookie1", season=2024, score=0.72, startup_adp=54.0)

    result = TrendEngine(phase2_seed_data).compute_trend("rookie1")

    assert result.backfilled is True
    assert result.seasons_compared == 1
    assert result.trend_label in {"will_rise", "will_maintain", "will_fall"}


def test_trend_adp_delta(phase2_seed_data):
    _insert_trend_row(phase2_seed_data, player_id="wrb1", season=2023, score=0.42, startup_adp=48.0)
    _insert_trend_row(phase2_seed_data, player_id="wrb1", season=2024, score=0.70, startup_adp=24.0)

    result = TrendEngine(phase2_seed_data).compute_trend("wrb1")

    assert result.adp_delta is not None
    assert result.adp_delta > 0
