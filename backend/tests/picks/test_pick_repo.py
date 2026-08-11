from __future__ import annotations

from datetime import datetime, timezone

from fantasy.picks.constants import DraftTiebreaker, NonPlayoffOrderBasis, PlayoffOrdering
from fantasy.picks.models import LeagueDraftOrderRule, PickValue, TimingLabel
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


def _seed_rookie_draft_selections(conn, *, pick_count: int) -> None:
    conn.executemany(
        """
        INSERT INTO draft_pick_selections (
            id, league_id, draft_id, roster_id, player_id, pick_slot,
            round_number, season, draft_type, position, archetype_label, ingested_at
        )
        VALUES (?, 'league_x', 'draft_2026', ?, ?, ?, ?, 2026, 'rookie', 'RB', 'rookie', CURRENT_TIMESTAMP)
        """,
        [
            (
                pick_slot,
                ((pick_slot - 1) % 3) + 1,
                f"rookie_{pick_slot}",
                pick_slot,
                ((pick_slot - 1) // 3) + 1,
            )
            for pick_slot in range(1, pick_count + 1)
        ],
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


def test_get_all_picks_rolls_window_after_completed_rookie_draft(db):
    _seed_league(db)
    db.execute(
        """
        INSERT INTO traded_picks (id, league_id, season, round, roster_id, owner_id, previous_owner_id)
        VALUES
            (1, 'league_x', '2026', 1, 2, '1', '2'),
            (2, 'league_x', '2029', 1, 3, '1', '3')
        """
    )
    _seed_rookie_draft_selections(db, pick_count=9)

    picks = PickRepo(db).get_all_picks("league_x", current_owner_roster_id=1)

    assert {pick.pick_year for pick in picks} == {2027, 2028, 2029}
    assert len(picks) == 10
    assert any(
        pick.pick_owner_roster_id == 3 and pick.pick_year == 2029 and pick.pick_round == 1
        for pick in picks
    )


def test_get_all_picks_keeps_current_year_during_partial_rookie_draft(db):
    _seed_league(db)
    _seed_rookie_draft_selections(db, pick_count=1)

    picks = PickRepo(db).get_all_picks("league_x")

    assert {pick.pick_year for pick in picks} == {2026, 2027, 2028}


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


def test_get_current_strength_slots_ranks_complete_scorecards(db):
    _seed_league(db)
    db.execute(
        """
        INSERT INTO team_scorecards (
            id, league_id, roster_id, win_now, future_value, depth,
            pick_capital, flexibility, fragility, age_risk, liquidity,
            positional_insulation, composite, computation_json
        )
        VALUES
            (1, 'league_x', 1, 0.1, 0, 0, 0, 0, 0, 0, 0, 0, 0, '{}'),
            (2, 'league_x', 2, 0.5, 0, 0, 0, 0, 0, 0, 0, 0, 0, '{}'),
            (3, 'league_x', 3, 0.9, 0, 0, 0, 0, 0, 0, 0, 0, 0, '{}')
        """
    )

    assert PickRepo(db).get_current_strength_slots("league_x") == {
        1: 1.0,
        2: 2.0,
        3: 3.0,
    }


def test_get_draft_order_rule_returns_none_when_unconfigured(db):
    repo = PickRepo(db)
    assert repo.get_draft_order_rule("missing_league") is None


def test_save_and_get_draft_order_rule_roundtrip(db):
    _seed_league(db)
    repo = PickRepo(db)
    rule = LeagueDraftOrderRule(
        non_playoff_basis=NonPlayoffOrderBasis.INVERSE_STANDINGS,
        playoff_ordering=PlayoffOrdering.BY_FINISH,
        tiebreaker=DraftTiebreaker.POINTS_AGAINST,
    )

    repo.save_draft_order_rule("league_x", rule)
    saved = repo.get_draft_order_rule("league_x")

    assert saved is not None
    assert saved == rule


def test_save_draft_order_rule_upsert(db):
    _seed_league(db)
    repo = PickRepo(db)
    repo.save_draft_order_rule(
        "league_x",
        LeagueDraftOrderRule(
            non_playoff_basis=NonPlayoffOrderBasis.INVERSE_STANDINGS,
            playoff_ordering=PlayoffOrdering.BY_FINISH,
            tiebreaker=DraftTiebreaker.POINTS_AGAINST,
        ),
    )
    repo.save_draft_order_rule(
        "league_x",
        LeagueDraftOrderRule(
            non_playoff_basis=NonPlayoffOrderBasis.MAX_POINTS_FOR,
            playoff_ordering=PlayoffOrdering.BY_RECORD,
            tiebreaker=DraftTiebreaker.POINTS_FOR,
        ),
    )

    saved = repo.get_draft_order_rule("league_x")

    assert saved is not None
    assert saved.non_playoff_basis == NonPlayoffOrderBasis.MAX_POINTS_FOR
    assert saved.playoff_ordering == PlayoffOrdering.BY_RECORD
    assert saved.tiebreaker == DraftTiebreaker.POINTS_FOR


def test_get_max_pf_slots_ranks_by_fpts_asc(db):
    _seed_league(db)
    db.execute(
        """
        INSERT INTO standings (id, league_id, roster_id, wins, losses, ties, fpts, fpts_against)
        VALUES
            (1, 'league_x', 1, 0, 0, 0, 100.0, 0.0),
            (2, 'league_x', 2, 0, 0, 0, 200.0, 0.0),
            (3, 'league_x', 3, 0, 0, 0, 150.0, 0.0)
        """
    )

    repo = PickRepo(db)

    assert repo.get_max_pf_slots("league_x") == {1: 1, 3: 2, 2: 3}


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
