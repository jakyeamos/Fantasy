from __future__ import annotations

from fantasy.prospects.draft_capital_refresh import (
    ActualDraftPick,
    refresh_actual_draft_capital,
)


def test_refresh_actual_draft_capital_updates_features_and_rebuilds_board(db):
    db.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions,
            settings_blob, superflex, tep, ppr
        )
        VALUES (
            'league_x', 'League X', '2026', '{}', '[]', '{"num_teams":12}', TRUE, FALSE, 0.5
        )
        """
    )
    db.execute(
        """
        INSERT INTO historical_prospect_features (
            player_id, draft_year, position, player_name, draft_ovr, adp,
            college_rush_ypg, college_rec_ypg, college_ypc, college_mkt_share_proxy,
            college_td_rate, forty, weight, height, age_at_draft
        )
        VALUES (
            'price', 2026, 'RB', 'Jadarian Price', 48, 48,
            84.8, 7.25, 5.96, 0.848, 0.097, 4.49, 203, 71, 22.0
        )
        """
    )
    db.execute(
        """
        INSERT INTO prospect_model_outputs (
            league_id, draft_season, player_id, player_name, position,
            archetype_label, hit_rate_bucket, tier, predicted_tier, predicted_bucket,
            risk_band, low_confidence, comps_json
        )
        VALUES (
            'league_x', 2026, 'price', 'Jadarian Price', 'RB',
            'Passing-Down RB', 'Low hit rate', 1, 1, 'mediocre',
            'Low', FALSE, '[]'
        )
        """
    )

    result = refresh_actual_draft_capital(
        db,
        draft_year=2026,
        picks=[
            ActualDraftPick(
                player_name="Jadarian Price",
                position="RB",
                pick=32,
                team="Seattle Seahawks",
                college="Notre Dame",
                source="test",
            )
        ],
    )

    assert result["matched_rows"] == 1
    assert result["updated_rows"] == 1
    assert result["rebuilt_boards"] == 1
    assert db.execute(
        """
        SELECT draft_ovr
        FROM historical_prospect_features
        WHERE player_id = 'price'
        """
    ).fetchone() == (32,)
    board_json = db.execute(
        """
        SELECT board_json
        FROM rookie_board_cache
        WHERE league_id = 'league_x'
        """
    ).fetchone()
    assert board_json is not None


def test_refresh_actual_draft_capital_fuzzy_matches_close_names(db):
    db.execute(
        """
        INSERT INTO historical_prospect_features (
            player_id, draft_year, position, player_name, draft_ovr
        )
        VALUES ('love', 2026, 'RB', 'Jeremiyah Love', 12)
        """
    )

    result = refresh_actual_draft_capital(
        db,
        draft_year=2026,
        picks=[
            ActualDraftPick(
                player_name="Jeremiah Love",
                position="RB",
                pick=3,
                source="test",
            )
        ],
        rebuild_boards=False,
    )

    assert result["matched_rows"] == 1
    assert db.execute(
        """
        SELECT draft_ovr
        FROM historical_prospect_features
        WHERE player_id = 'love'
        """
    ).fetchone() == (3,)


def test_refresh_actual_draft_capital_matches_unique_surname_alias(db):
    db.execute(
        """
        INSERT INTO historical_prospect_features (
            player_id, draft_year, position, player_name, draft_ovr
        )
        VALUES ('concepcion', 2026, 'WR', 'Kevin Concepcion', 34)
        """
    )

    result = refresh_actual_draft_capital(
        db,
        draft_year=2026,
        picks=[
            ActualDraftPick(
                player_name="KC Concepcion",
                position="WR",
                pick=24,
                source="test",
            )
        ],
        rebuild_boards=False,
    )

    assert result["matched_rows"] == 1
    assert db.execute(
        """
        SELECT draft_ovr
        FROM historical_prospect_features
        WHERE player_id = 'concepcion'
        """
    ).fetchone() == (24,)
