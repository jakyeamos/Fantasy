from __future__ import annotations

from datetime import datetime, timezone

from fantasy.picks.models import PickValue, TimingLabel
from fantasy.picks.pick_repo import PickRepo
from fantasy.trade.models import TradeAsset


def _seed_league(conn) -> None:
    conn.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions,
            settings_blob, superflex, tep, ppr
        )
        VALUES (
            'league_x',
            'League X',
            '2026',
            '{"rec":1.0}',
            '["QB","RB","WR","TE","SUPER_FLEX"]',
            '{"draft_rounds":3}',
            TRUE,
            FALSE,
            1.0
        )
        """
    )
    conn.execute(
        """
        INSERT INTO rosters (
            id, league_id, roster_id, owner_id, owner_display_name, starters, players, reserve, taxi
        )
        VALUES
            (1, 'league_x', 1, 'owner_a', 'Alpha', '[]', '[]', '[]', '[]'),
            (2, 'league_x', 2, 'owner_b', 'Beta', '[]', '[]', '[]', '[]'),
            (3, 'league_x', 3, 'owner_c', 'Gamma', '[]', '[]', '[]', '[]')
        """
    )


def test_get_standings_returns_neutral_fallback_when_missing(db):
    _seed_league(db)
    repo = PickRepo(db)
    standings = repo.get_standings(1, "league_x")
    assert standings.win_pct == 0.5
    assert standings.remaining_games == 14


def test_get_manager_demand_factor_uses_direction_and_transactions(db):
    _seed_league(db)
    db.execute(
        """
        INSERT INTO team_directions (
            id, league_id, roster_id, primary_label, confidence, reasoning,
            alternates_json, delta_json, approved_moves, discouraged_moves
        )
        VALUES
            (1, 'league_x', 1, 'hard_rebuild', 0.9, 'seeded', '[]', '{}', '[]', '[]'),
            (2, 'league_x', 2, 'true_contender', 0.9, 'seeded', '[]', '{}', '[]', '[]')
        """
    )
    for index in range(10):
        db.execute(
            """
            INSERT INTO transactions (
                transaction_id, league_id, type, status, created_at,
                roster_ids, adds, drops, draft_picks, week
            )
            VALUES (?, 'league_x', 'trade', 'complete', CURRENT_TIMESTAMP, '[1,2]', '{}', '{}', ?, ?)
            """,
            [
                f"tx_{index}",
                '[{"season":"2027","round":1,"roster_id":1,"owner_id":1,"previous_owner_id":2}]',
                index + 1,
            ],
        )
    repo = PickRepo(db)
    assert repo.get_manager_demand_factor(1, "league_x") > repo.get_manager_demand_factor(2, "league_x")


def test_get_all_picks_derives_inventory_from_traded_picks(db):
    _seed_league(db)
    db.execute(
        """
        INSERT INTO traded_picks (id, league_id, season, round, roster_id, owner_id, previous_owner_id)
        VALUES (1, 'league_x', '2026', 1, 2, '1', '2')
        """
    )
    repo = PickRepo(db)
    picks = repo.get_all_picks("league_x")
    assert len(picks) == 27
    assert any(
        pick.pick_owner_roster_id == 2 and pick.pick_year == 2026 and pick.pick_round == 1
        for pick in picks
    )


def test_get_all_picks_can_filter_by_current_owner(db):
    _seed_league(db)
    db.execute(
        """
        INSERT INTO traded_picks (id, league_id, season, round, roster_id, owner_id, previous_owner_id)
        VALUES (1, 'league_x', '2026', 1, 2, '1', '2')
        """
    )
    repo = PickRepo(db)
    picks = repo.get_all_picks("league_x", current_owner_roster_id=1)
    assert len(picks) == 10
    assert any(
        pick.pick_owner_roster_id == 2 and pick.pick_year == 2026 and pick.pick_round == 1
        for pick in picks
    )
    assert all(
        not (
            pick.pick_owner_roster_id == 2
            and pick.pick_year != 2026
            and pick.pick_round == 1
        )
        for pick in picks
    )


def test_get_class_strength_signal_reads_latest_cache(db):
    _seed_league(db)
    db.execute(
        """
        INSERT INTO rookie_board_cache (id, league_id, computed_at, class_strength_signal, board_json)
        VALUES
            (1, 'league_x', '2026-01-01T00:00:00', -0.2, '{}'),
            (2, 'league_x', '2026-02-01T00:00:00', 0.35, '{}')
        """
    )
    repo = PickRepo(db)
    assert repo.get_class_strength_signal("league_x") == 0.35


def test_save_pick_values_persists_rows(db):
    _seed_league(db)
    repo = PickRepo(db)
    value = PickValue(
        pick=TradeAsset(
            asset_type="pick",
            pick_owner_roster_id=1,
            pick_year=2026,
            pick_round=1,
        ),
        base_value=100.0,
        timed_value=110.0,
        league_adjusted_value=115.0,
        demand_adjusted_value=120.0,
        expected_draft_slot=1.0,
        timing_label=TimingLabel.SELL_NOW,
        timing_reasoning="Near peak rookie fever window.",
        class_strength_signal=0.1,
        years_out=0,
        computed_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
    )
    repo.save_pick_values("league_x", [value])
    row = db.execute(
        """
        SELECT demand_adjusted_value, years_out
        FROM pick_values
        WHERE league_id = 'league_x' AND pick_owner_roster_id = 1 AND pick_year = 2026 AND pick_round = 1
        """
    ).fetchone()
    assert row == (120.0, 0)
