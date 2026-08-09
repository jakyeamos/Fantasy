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


def test_gap_surfacing_missing_sleeper_stat_weeks():
    gaps = GapDetector.detect_missing_stat_weeks([1, 2, 3], {1, 3})

    assert len(gaps) == 1
    assert gaps[0].name == "Missing Sleeper Weekly Stats"
    assert "week(s) 2" in gaps[0].reason


def test_sleeper_native_stats_skip_nflverse_mapping_gaps(db):
    gaps = GapDetector.collect_all(
        conn=db,
        league_id="league_x",
        scoring_settings={"rec": 1.0, "def_td": 6.0},
        sleeper_to_nfldata_map={},
        stats_df=pl.DataFrame({"season": [2025]}),
        expected_years=[2025],
        stats_source="sleeper",
    )

    assert not any(gap.name.startswith("Unmapped Scoring Key") for gap in gaps)
