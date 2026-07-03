from __future__ import annotations

import json

from fantasy.edge_radar.engine import EdgeRadarEngine
from fantasy.edge_radar.player_metadata import (
    PlayerMetadataRefreshService,
    import_curated_dense_player_metadata,
    import_player_metadata_csv,
)


def test_import_player_metadata_csv_loads_sourced_dense_metrics(db, tmp_path):
    db.execute(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES (
            'luther_burden', 'Luther Burden', 'WR', 'CHI', 22,
            '{"target_share":0.29}'
        )
        """
    )
    csv_path = tmp_path / "dense_player_metadata.csv"
    csv_path.write_text(
        "\n".join(
            [
                "player_id,player_name,yprr,route_participation,snap_share,first_read_share,slot_rate,source,notes",
                "luther_burden,Luther Burden,3.15,0.91,0.84,0.32,0.54,manual_research,public YPRR lookup",
                "missing_player,Missing Player,2.2,0.8,0.7,0.2,0.4,manual_research,no match",
            ]
        ),
        encoding="utf-8",
    )

    summary = import_player_metadata_csv(db, csv_path)

    metadata = json.loads(
        db.execute(
            "SELECT metadata_blob FROM players WHERE player_id = 'luther_burden'"
        ).fetchone()[0]
    )

    assert summary.source_rows == 2
    assert summary.matched_rows == 1
    assert summary.updated_rows == 1
    assert summary.unmatched_rows == 1
    assert metadata["target_share"] == 0.29
    assert metadata["yards_per_route_run"] == 3.15
    assert metadata["route_participation"] == 0.91
    assert metadata["snap_share"] == 0.84
    assert metadata["first_read_target_share"] == 0.32
    assert metadata["slot_rate"] == 0.54
    assert metadata["dense_metadata_source"] == "manual_research"
    assert metadata["dense_metadata_notes"] == "public YPRR lookup"

    health_by_source = {
        source.source: source for source in EdgeRadarEngine(db).build().source_health
    }
    assert health_by_source["player_dense_metadata"].status == "ready"


def test_import_curated_dense_player_metadata_uses_default_repo_path(
    monkeypatch,
    db,
    tmp_path,
):
    db.execute(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES ('wr1', 'WR One', 'WR', 'SEA', 24, '{}')
        """
    )
    csv_path = tmp_path / "player_dense_metadata.csv"
    csv_path.write_text(
        "\n".join(
            [
                (
                    "player_id,player_name,yprr,route_participation,snap_share,"
                    "first_read_share,source,notes"
                ),
                "wr1,WR One,2.4,0.86,0.78,0.22,manual_research,default import",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "fantasy.edge_radar.player_metadata.DENSE_PLAYER_METADATA_CSV_PATH",
        csv_path,
    )

    summary = import_curated_dense_player_metadata(db)

    metadata = json.loads(
        db.execute(
            "SELECT metadata_blob FROM players WHERE player_id = 'wr1'"
        ).fetchone()[0]
    )
    assert summary.updated_rows == 1
    assert metadata["yards_per_route_run"] == 2.4
    assert metadata["route_participation"] == 0.86
    assert metadata["snap_share"] == 0.78
    assert metadata["first_read_target_share"] == 0.22


def test_import_player_metadata_csv_falls_back_to_unique_player_name(db, tmp_path):
    db.execute(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES ('wr1', 'WR One', 'WR', 'SEA', 24, '{}')
        """
    )
    csv_path = tmp_path / "dense_player_metadata.csv"
    csv_path.write_text(
        "\n".join(
            [
                (
                    "player_id,player_name,yprr,route_participation,snap_share,"
                    "first_read_share,source,notes"
                ),
                "provider_wr1,WR One,2.4,0.86,0.78,0.22,manual_research,name match",
            ]
        ),
        encoding="utf-8",
    )

    summary = import_player_metadata_csv(db, csv_path)

    metadata = json.loads(
        db.execute(
            "SELECT metadata_blob FROM players WHERE player_id = 'wr1'"
        ).fetchone()[0]
    )
    assert summary.matched_rows == 1
    assert summary.updated_rows == 1
    assert metadata["yards_per_route_run"] == 2.4


def test_edge_radar_dense_metadata_health_requires_all_dense_markers(db):
    db.execute(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES ('wr1', 'WR One', 'WR', 'SEA', 24, '{"yards_per_route_run":2.4}')
        """
    )

    health_by_source = {
        source.source: source for source in EdgeRadarEngine(db).build().source_health
    }

    assert health_by_source["player_dense_metadata"].status == "missing"


def test_player_metadata_refresh_derives_usage_growth_and_market_signals(db):
    db.execute(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES
            (
                'wr1', 'WR One', 'WR', 'SEA', 24,
                '{"route_participation":0.91,"first_read_target_share":0.32}'
            ),
            ('wr2', 'WR Two', 'WR', 'SEA', 25, '{}'),
            ('rb1', 'RB One', 'RB', 'SEA', 23, '{}')
        """
    )
    db.execute(
        """
        INSERT INTO player_stats_weekly (
            player_id, player_name, position, season, week,
            targets, receiving_yards, carries, rushing_yards, fantasy_points
        )
        VALUES
            ('wr1', 'WR One', 'WR', 2026, 1, 8, 80, 0, 0, 16),
            ('wr1', 'WR One', 'WR', 2026, 2, 12, 110, 0, 0, 22),
            ('wr2', 'WR Two', 'WR', 2026, 1, 5, 40, 0, 0, 8),
            ('wr2', 'WR Two', 'WR', 2026, 2, 5, 45, 0, 0, 9),
            ('rb1', 'RB One', 'RB', 2026, 1, 2, 15, 14, 70, 13),
            ('rb1', 'RB One', 'RB', 2026, 2, 2, 20, 16, 90, 17),
            ('wr1', 'WR One', 'WR', 2025, 1, 4, 35, 0, 0, 7),
            ('wr1', 'WR One', 'WR', 2025, 2, 6, 55, 0, 0, 11)
        """
    )
    db.execute(
        """
        INSERT INTO market_values (
            id, player_id, fantasycalc_value, fantasycalc_rank,
            fantasycalc_trend30, adp_baseline
        )
        VALUES (1, 'wr1', 8400, 24, 550, 91)
        """
    )

    summary = PlayerMetadataRefreshService(db).refresh(2026)

    metadata = json.loads(
        db.execute(
            "SELECT metadata_blob FROM players WHERE player_id = 'wr1'"
        ).fetchone()[0]
    )

    assert summary.season == 2026
    assert summary.source_rows == 3
    assert summary.updated_rows == 3
    assert metadata["target_share"] == 0.59
    assert metadata["weekly_targets"] == 10.0
    assert metadata["yoy_role_growth"] == 1.0
    assert metadata["trade_value_movement"] == 0.07
    assert metadata["route_participation"] == 0.91
    assert metadata["first_read_target_share"] == 0.32


def test_edge_radar_source_health_reports_player_metadata_refresh(db):
    db.execute(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES ('wr1', 'WR One', 'WR', 'SEA', 24, '{}')
        """
    )
    db.execute(
        """
        INSERT INTO player_stats_weekly (
            player_id, player_name, position, season, week,
            targets, receiving_yards, carries, fantasy_points
        )
        VALUES ('wr1', 'WR One', 'WR', 2026, 1, 8, 80, 0, 16)
        """
    )
    db.execute(
        """
        INSERT INTO market_values (
            id, player_id, fantasycalc_value, fantasycalc_rank,
            fantasycalc_trend30, adp_baseline
        )
        VALUES (1, 'wr1', 8400, 24, 550, 91)
        """
    )

    PlayerMetadataRefreshService(db).refresh(2026)

    health_by_source = {
        source.source: source for source in EdgeRadarEngine(db).build().source_health
    }

    assert health_by_source["player_usage_metadata"].status == "ready"
    assert health_by_source["player_market_metadata"].status == "ready"
