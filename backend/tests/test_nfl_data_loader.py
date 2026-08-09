from __future__ import annotations

import polars as pl
import pytest

from fantasy.ingestion.nfl_data_loader import (
    NflDataPyLoader,
    PLAYER_STATS_COLUMNS,
    compute_fantasy_points,
    load_adp_baseline,
    refresh_market_from_fantasycalc,
    refresh_adp_baseline_from_fantasycalc,
)
from fantasy.market.models import ExternalPlayerValue


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
    monkeypatch.setattr(
        pl,
        "read_parquet",
        lambda _url: pl.DataFrame(
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
    monkeypatch.setattr(
        pl,
        "read_parquet",
        lambda _url: pl.DataFrame({"season": pl.Series([], dtype=pl.Int64)}),
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


@pytest.mark.asyncio
async def test_refresh_adp_baseline_from_fantasycalc_matches_by_name(monkeypatch, db):
    db.execute(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES
            ('p_wr', 'Rome Odunze', 'WR', 'CHI', 22, '{}'),
            ('p_rb', 'Jahmyr Gibbs', 'RB', 'DET', 23, '{}')
        """
    )

    async def _fake_fetch(self, *, num_qbs: int, num_teams: int, ppr: float):
        assert num_qbs == 2
        assert num_teams == 12
        assert ppr == 1.0
        return [
            ExternalPlayerValue(
                player_name="Rome Odunze",
                position="WR",
                dynasty_value=5000.0,
                overall_rank=21,
                mfl_id=None,
            ),
            ExternalPlayerValue(
                player_name="Jahmyr Gibbs",
                position="RB",
                dynasty_value=9000.0,
                overall_rank=5,
                mfl_id=None,
            ),
        ]

    monkeypatch.setattr(
        "fantasy.ingestion.nfl_data_loader.FantasyCalcClient.fetch_dynasty_values",
        _fake_fetch,
    )

    summary = await refresh_adp_baseline_from_fantasycalc(
        db,
        num_qbs=2,
        num_teams=12,
        ppr=1.0,
    )

    assert summary["source_rows"] == 2
    assert summary["matched_rows"] == 2
    assert summary["matched_unique_rows"] == 2
    assert summary["unmatched_rows"] == 0

    rows = db.execute(
        """
        SELECT player_id, player_name, position, adp, adp_source
        FROM player_adp_baseline
        ORDER BY adp ASC
        """
    ).fetchall()
    assert rows == [
        ("p_rb", "Jahmyr Gibbs", "RB", 5.0, "fantasycalc_api"),
        ("p_wr", "Rome Odunze", "WR", 21.0, "fantasycalc_api"),
    ]


@pytest.mark.asyncio
async def test_market_refresh_populates_adp_and_external_values_atomically(monkeypatch, db):
    db.execute(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES
            ('p_wr', 'Rome Odunze', 'WR', 'CHI', 22, '{}'),
            ('p_rb', 'Jahmyr Gibbs', 'RB', 'DET', 23, '{}')
        """
    )

    async def _fake_fetch(self, *, num_qbs: int, num_teams: int, ppr: float):
        return [
            ExternalPlayerValue(
                player_name="Rome Odunze",
                position="WR",
                dynasty_value=5000.0,
                overall_rank=21,
                trend_30day=125.0,
                mfl_id=None,
            ),
            ExternalPlayerValue(
                player_name="Jahmyr Gibbs",
                position="RB",
                dynasty_value=9000.0,
                overall_rank=5,
                trend_30day=-25.0,
                mfl_id=None,
            ),
        ]

    monkeypatch.setattr(
        "fantasy.ingestion.nfl_data_loader.FantasyCalcClient.fetch_dynasty_values",
        _fake_fetch,
    )

    summary = await refresh_market_from_fantasycalc(db, num_qbs=2, num_teams=12, ppr=1.0)

    assert summary == {
        "refresh_run_id": 1,
        "source_rows": 2,
        "matched_rows": 2,
        "matched_unique_rows": 2,
        "unmatched_rows": 0,
        "market_value_rows": 2,
        "coverage_ratio": 1.0,
    }
    assert db.execute(
        """
        SELECT player_id, fantasycalc_value, fantasycalc_rank,
               fantasycalc_trend30, adp_baseline
        FROM market_values
        ORDER BY fantasycalc_rank
        """
    ).fetchall() == [
        ("p_rb", 9000.0, 5, -25.0, 5.0),
        ("p_wr", 5000.0, 21, 125.0, 21.0),
    ]
    assert db.execute(
        """
        SELECT status, source, num_qbs, num_teams, ppr, source_rows,
               matched_unique_rows, coverage_ratio
        FROM market_refresh_runs
        """
    ).fetchall() == [
        ("success", "fantasycalc_api", 2, 12, 1.0, 2, 2, 1.0)
    ]


@pytest.mark.asyncio
async def test_refresh_adp_baseline_from_fantasycalc_does_not_wipe_on_no_matches(
    monkeypatch, db
):
    db.execute(
        """
        INSERT INTO player_adp_baseline (player_id, player_name, position, adp, adp_source)
        VALUES ('existing', 'Existing Player', 'WR', 77.0, 'seed')
        """
    )

    async def _fake_fetch(self, *, num_qbs: int, num_teams: int, ppr: float):
        return [
            ExternalPlayerValue(
                player_name="Unmatched Name",
                position="WR",
                dynasty_value=100.0,
                overall_rank=88,
                mfl_id=None,
            )
        ]

    monkeypatch.setattr(
        "fantasy.ingestion.nfl_data_loader.FantasyCalcClient.fetch_dynasty_values",
        _fake_fetch,
    )

    with pytest.raises(ValueError, match="matched zero players"):
        await refresh_adp_baseline_from_fantasycalc(db)

    rows = db.execute(
        """
        SELECT player_id, player_name, adp, adp_source
        FROM player_adp_baseline
        """
    ).fetchall()
    assert rows == [("existing", "Existing Player", 77.0, "seed")]
    assert db.execute(
        """
        SELECT status, source_rows, matched_unique_rows, coverage_ratio, error_detail
        FROM market_refresh_runs
        """
    ).fetchall() == [
        ("failure", 1, 0, 0.0, "FantasyCalc market refresh matched zero local players.")
    ]


@pytest.mark.asyncio
async def test_market_refresh_records_provider_failure(monkeypatch, db):
    async def _failed_fetch(self, *, num_qbs: int, num_teams: int, ppr: float):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(
        "fantasy.ingestion.nfl_data_loader.FantasyCalcClient.fetch_dynasty_values",
        _failed_fetch,
    )

    with pytest.raises(RuntimeError, match="provider unavailable"):
        await refresh_market_from_fantasycalc(db, num_qbs=2, num_teams=12, ppr=0.5)

    assert db.execute(
        """
        SELECT status, source_rows, coverage_ratio, error_detail
        FROM market_refresh_runs
        """
    ).fetchall() == [("failure", None, None, "provider unavailable")]
