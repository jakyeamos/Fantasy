from __future__ import annotations

from fantasy.portfolio.portfolio_repo import PortfolioRepo


def _seed_portfolio_data(conn) -> None:
    conn.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions, settings_blob, superflex, tep, ppr
        )
        VALUES
            ('league_a', 'League A', '2025', '{}', '[]', '{"num_teams":2}', FALSE, FALSE, 0.0),
            ('league_b', 'League B', '2025', '{}', '[]', '{"num_teams":2}', FALSE, FALSE, 0.0),
            ('league_c', 'League C', '2025', '{}', '[]', '{"num_teams":2}', FALSE, FALSE, 0.0)
        """
    )
    conn.execute(
        """
        INSERT INTO rosters (id, league_id, roster_id, owner_id, owner_display_name, players, starters, reserve, taxi)
        VALUES
            (1, 'league_a', 1, 'portfolio_user', 'jakye', '["alpha","beta"]', '[]', '[]', '[]'),
            (2, 'league_a', 2, 'other_user_a', 'other-a', '["other_a"]', '[]', '[]', '[]'),
            (3, 'league_b', 1, 'portfolio_user', 'jakye', '["alpha","gamma"]', '[]', '[]', '[]'),
            (4, 'league_b', 2, 'other_user_b', 'other-b', '["other_b"]', '[]', '[]', '[]'),
            (5, 'league_c', 1, 'portfolio_user', 'jakye', '["alpha","delta"]', '[]', '[]', '[]'),
            (6, 'league_c', 2, 'other_user_c', 'other-c', '["other_c"]', '[]', '[]', '[]')
        """
    )
    conn.execute(
        """
        INSERT INTO players (player_id, full_name, position, team, metadata_blob)
        VALUES
            ('alpha', 'Alpha Wideout', 'WR', 'SF', '{}'),
            ('beta', 'Beta Back', 'RB', 'KC', '{}'),
            ('gamma', 'Gamma Wideout', 'WR', 'SF', '{}'),
            ('delta', 'Delta Quarterback', 'QB', 'DAL', '{}'),
            ('other_a', 'Other A', 'WR', 'CHI', '{}'),
            ('other_b', 'Other B', 'RB', 'ATL', '{}'),
            ('other_c', 'Other C', 'TE', 'LAR', '{}')
        """
    )


def test_load_exposure_rows_counts_only_portfolio_rosters(db):
    _seed_portfolio_data(db)

    rows = PortfolioRepo(db).load_exposure_rows()
    rows_by_id = {row.player_id: row for row in rows}

    assert rows_by_id["alpha"].league_count == 3
    assert rows_by_id["alpha"].owned_in_leagues == ["league_a", "league_b", "league_c"]
    assert rows_by_id["beta"].league_count == 1
    assert "other_a" not in rows_by_id


def test_load_correlated_risk_rows_detects_multi_league_team_cluster(db):
    _seed_portfolio_data(db)

    rows = PortfolioRepo(db).load_correlated_risk_rows()

    assert len(rows) == 1
    row = rows[0]
    assert row.nfl_team == "SF"
    assert row.league_ids == ["league_a", "league_b", "league_c"]
    assert {player.full_name for player in row.players} >= {"Alpha Wideout", "Gamma Wideout"}


def test_load_exposure_rows_can_scope_to_explicit_owner(db):
    _seed_portfolio_data(db)

    rows = PortfolioRepo(db).load_exposure_rows(owner_id="other_user_b")

    assert len(rows) == 1
    assert rows[0].player_id == "other_b"
    assert rows[0].owned_in_leagues == ["league_b"]


def test_save_retrospective_run_updates_health_timestamp(db):
    repo = PortfolioRepo(db)

    assert repo.get_last_recalibration() is None
    repo.save_retrospective_run(
        run_type="direction_labels",
        season="2025",
        grades_json={"overall_accuracy": 1.0},
    )

    last_run = repo.get_last_recalibration()
    assert last_run is not None
