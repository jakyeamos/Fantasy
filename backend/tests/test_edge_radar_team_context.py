from __future__ import annotations

from fantasy.edge_radar.team_context import import_team_context_csv


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
