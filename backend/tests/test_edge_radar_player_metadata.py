from __future__ import annotations

import json

from fantasy.edge_radar.engine import EdgeRadarEngine
from fantasy.edge_radar.player_metadata import PlayerMetadataRefreshService


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
