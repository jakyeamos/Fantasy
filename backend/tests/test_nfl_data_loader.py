from __future__ import annotations

import sys
from types import SimpleNamespace

import polars as pl
import pytest

from fantasy.ingestion.nfl_data_loader import (
    NflDataPyLoader,
    PLAYER_STATS_COLUMNS,
    compute_fantasy_points,
    load_adp_baseline,
)


def test_compute_fantasy_points_maps_stats_and_te_bonus():
    total, unmapped = compute_fantasy_points(
        {
            "receptions": 5,
            "receiving_yards": 80,
            "receiving_tds": 1,
        },
        {"rec": 1.0, "rec_yd": 0.1, "rec_td": 6.0, "bonus_rec_te": 0.5, "mystery": 2.0},
        "TE",
    )

    assert total == 21.5
    assert unmapped == ["mystery"]


def test_load_weekly_stats_pads_missing_columns(monkeypatch):
    fake_source = SimpleNamespace(empty=False)
    monkeypatch.setitem(
        sys.modules,
        "nfl_data_py",
        SimpleNamespace(import_weekly_data=lambda years: fake_source),
    )
    monkeypatch.setattr(
        pl,
        "from_pandas",
        lambda _value: pl.DataFrame(
            {
                "player_id": ["p1"],
                "player_name": ["Player One"],
                "position": ["WR"],
                "season": [2025],
                "week": [1],
                "receptions": [5.0],
            }
        ),
    )

    df = NflDataPyLoader().load_weekly_stats([2025])

    assert df.columns == PLAYER_STATS_COLUMNS
    assert df.height == 1
    assert df["player_id"].to_list() == ["p1"]
    assert df["fantasy_points"].to_list() == [None]


def test_load_weekly_stats_returns_empty_frame_for_empty_source(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "nfl_data_py",
        SimpleNamespace(import_weekly_data=lambda years: SimpleNamespace(empty=True)),
    )

    df = NflDataPyLoader().load_weekly_stats([2025])

    assert df.height == 0
    assert df.columns == PLAYER_STATS_COLUMNS


def test_load_adp_baseline_requires_sleeper_ids(db, tmp_path):
    path = tmp_path / "adp.csv"
    path.write_text("player_name,position,adp\nPlayer One,WR,12.5\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Sleeper player ID column"):
        load_adp_baseline(db, str(path))


def test_load_adp_baseline_rejects_rows_missing_ids(db, tmp_path):
    path = tmp_path / "adp.csv"
    path.write_text("player_id,player_name,position,adp\n,Player One,WR,12.5\n", encoding="utf-8")

    with pytest.raises(ValueError, match="missing a Sleeper player ID"):
        load_adp_baseline(db, str(path))
