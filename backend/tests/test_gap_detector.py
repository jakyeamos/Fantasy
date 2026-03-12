import polars as pl

from fantasy.ingestion.gap_detector import GapDetector


def test_gap_surfacing(db):
    gaps = GapDetector.detect_unmapped_scoring_keys(
        scoring_settings={"rec": 1.0, "def_td": 6.0},
        sleeper_to_nfldata_map={"rec": "receptions"},
    )

    assert len(gaps) == 1
    assert "def_td" in gaps[0].name


def test_gap_surfacing_missing_year():
    df = pl.DataFrame(schema={"season": pl.Int64})
    gaps = GapDetector.detect_missing_season_stats(df, [2025])

    assert len(gaps) == 1
    assert "2025" in gaps[0].name
