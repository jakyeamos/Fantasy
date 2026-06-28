from __future__ import annotations

from fantasy.edge_radar.team_context import (
    TeamContextRefreshService,
    import_team_context_csv,
)
from fantasy.edge_radar.engine import EdgeRadarEngine


def test_import_team_context_csv_upserts_curated_source(db, tmp_path):
    csv_path = tmp_path / "team_context.csv"
    csv_path.write_text(
        "\n".join(
            [
                "season,team,head_coach,offensive_coordinator,play_caller,offensive_system,pace_label,pass_rate_label,source,notes",
                "2026,SEA,Coach A,OC A,OC A,wide_zone_play_action,neutral,balanced,manual_csv,initial",
                "2026,SEA,Coach B,OC B,OC B,spread,fast,pass_heavy,manual_csv,updated",
                "2026,MIA,Coach A,OC A,OC A,wide_zone_play_action,neutral,balanced,manual_csv,initial",
            ]
        ),
        encoding="utf-8",
    )

    summary = import_team_context_csv(db, csv_path)

    rows = db.execute(
        """
        SELECT team, season, head_coach, offensive_system, pace_label, notes
        FROM team_context_by_season
        ORDER BY team
        """
    ).fetchall()

    assert summary.source_rows == 3
    assert summary.upserted_rows == 3
    assert rows == [
        ("MIA", 2026, "Coach A", "wide_zone_play_action", "neutral", "initial"),
        ("SEA", 2026, "Coach B", "spread", "fast", "updated"),
    ]


def test_team_context_refresh_automates_environment_without_overwriting_curated_fields(db):
    db.execute(
        """
        INSERT INTO team_context_by_season (
            team, season, head_coach, offensive_coordinator, play_caller,
            offensive_system, source, notes
        )
        VALUES (
            'SEA', 2026, 'Coach A', 'OC A', 'OC A',
            'wide_zone_play_action', 'manual_csv', 'curated'
        )
        """
    )

    def _fake_team_stats_loader(season: int):
        assert season == 2026
        return [
            {
                "team": "SEA",
                "season": 2026,
                "plays": 1180,
                "games": 17,
                "pass_attempts": 690,
                "rush_attempts": 410,
                "points": 470,
            },
            {
                "team": "CAR",
                "season": 2026,
                "plays": 980,
                "games": 17,
                "pass_attempts": 440,
                "rush_attempts": 470,
                "points": 305,
            },
        ]

    summary = TeamContextRefreshService(
        db,
        team_stats_loader=_fake_team_stats_loader,
    ).refresh(2026)

    rows = db.execute(
        """
        SELECT team, season, head_coach, offensive_system, pace_label,
               pass_rate_label, source, notes
        FROM team_context_by_season
        ORDER BY team
        """
    ).fetchall()

    assert summary.season == 2026
    assert summary.environment_rows == 2
    assert summary.upserted_rows == 2
    assert rows == [
        (
            "CAR",
            2026,
            None,
            None,
            "slow",
            "run_heavy",
            "team_environment_nflreadpy",
            "automated team environment refresh",
        ),
        (
            "SEA",
            2026,
            "Coach A",
            "wide_zone_play_action",
            "fast",
            "pass_heavy",
            "manual_csv",
            "curated; automated team environment refresh",
        ),
    ]


def test_edge_radar_source_health_distinguishes_curated_and_environment_context(db):
    TeamContextRefreshService(
        db,
        team_stats_loader=lambda season: [
            {
                "team": "SEA",
                "season": season,
                "plays": 1180,
                "games": 17,
                "pass_attempts": 690,
                "rush_attempts": 410,
            }
        ],
    ).refresh(2026)

    health_by_source = {
        source.source: source for source in EdgeRadarEngine(db).build().source_health
    }

    assert health_by_source["team_context_curated"].status == "missing"
    assert health_by_source["team_environment_nflreadpy"].status == "ready"
