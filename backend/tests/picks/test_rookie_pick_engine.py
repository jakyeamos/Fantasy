from __future__ import annotations

import json

from pydantic import ValidationError

from fantasy.rookie.models import TendencyWarning
from fantasy.rookie_pick.models import DraftPickSelection
from fantasy.rookie_pick.rookie_pick_engine import RookiePickProfileEngine
from fantasy.rookie_pick.rookie_pick_repo import RookiePickRepo


def _seed_league(db) -> None:
    db.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions,
            settings_blob, superflex, tep, ppr
        )
        VALUES (
            'league_rookie',
            'League Rookie',
            '2026',
            '{"rec":1.0}',
            '["QB","RB","WR","TE","BN"]',
            '{"num_teams":2}',
            FALSE,
            FALSE,
            1.0
        )
        """
    )
    db.execute(
        """
        INSERT INTO rosters (
            id, league_id, roster_id, owner_id, owner_display_name, starters, players, reserve, taxi
        )
        VALUES
            (1, 'league_rookie', 1, 'user_a', 'Manager A', '[]', '[]', '[]', '[]'),
            (2, 'league_rookie', 2, 'user_b', 'Manager B', '[]', '[]', '[]', '[]')
        """
    )
    db.execute(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES
            ('wr_fast','Fast WR','WR','A',21,'{"forty":4.4}'),
            ('wr_slot','Slot WR','WR','A',22,'{"slot_rate":0.7}'),
            ('wr_big','Big WR','WR','A',22,'{"weight":215}'),
            ('rb_pow','Power RB','RB','A',22,'{"weight":225}'),
            ('rb_rec','Receiving RB','RB','A',22,'{"receiving_back":true}'),
            ('qb_mobile','Mobile QB','QB','A',22,'{"mobile":true}'),
            ('te_move','Move TE','TE','A',22,'{"move_te":true}')
        """
    )


def _insert_pick_trade(db, transaction_id: str, received_round: int, sent_round: int) -> None:
    draft_picks = [
        {
            "season": "2026",
            "round": received_round,
            "roster_id": 1,
            "owner_id": 1,
            "previous_owner_id": 2,
        },
        {
            "season": "2026",
            "round": sent_round,
            "roster_id": 2,
            "owner_id": 2,
            "previous_owner_id": 1,
        },
    ]
    db.execute(
        """
        INSERT INTO transactions (
            transaction_id, league_id, type, status, created_at,
            roster_ids, adds, drops, draft_picks, week
        )
        VALUES (?, 'league_rookie', 'trade', 'complete', CURRENT_TIMESTAMP, ?, '{}', '{}', ?, 1)
        """,
        [
            transaction_id,
            json.dumps([1, 2]),
            json.dumps(draft_picks),
        ],
    )


def _insert_selection(repo: RookiePickRepo, **kwargs) -> None:
    repo.upsert_draft_selection(
        DraftPickSelection(
            league_id="league_rookie",
            draft_id=kwargs.get("draft_id", "draft_startup"),
            roster_id=kwargs["roster_id"],
            player_id=kwargs["player_id"],
            pick_slot=kwargs["pick_slot"],
            round_number=kwargs["round_number"],
            season=kwargs.get("season", 2026),
            draft_type=kwargs.get("draft_type", "startup"),
            position=kwargs.get("position"),
            archetype_label=kwargs.get("archetype_label"),
        )
    )


def test_compute_profile_with_no_pick_trades_or_selections(db) -> None:
    _seed_league(db)
    profile = RookiePickProfileEngine(db).compute_profile("league_rookie", 1)

    assert profile.pick_premium_score is None
    assert profile.show_draft_picks_tab is False
    assert profile.pick_trade_evidence == 0


def test_compute_profile_with_insufficient_pick_trade_evidence(db) -> None:
    _seed_league(db)
    _insert_pick_trade(db, "trade_1", 2, 1)
    _insert_pick_trade(db, "trade_2", 2, 1)

    profile = RookiePickProfileEngine(db).compute_profile("league_rookie", 1)

    assert profile.pick_premium_score is None
    assert profile.pick_trade_evidence == 2


def test_compute_profile_with_positive_pick_premium_score(db) -> None:
    _seed_league(db)
    _insert_pick_trade(db, "trade_1", 2, 1)
    _insert_pick_trade(db, "trade_2", 2, 1)
    _insert_pick_trade(db, "trade_3", 2, 1)

    profile = RookiePickProfileEngine(db).compute_profile("league_rookie", 1)

    assert profile.pick_premium_score is not None
    assert profile.pick_premium_score > 0


def test_show_draft_picks_tab_appears_with_combined_evidence(db) -> None:
    _seed_league(db)
    repo = RookiePickRepo(db)
    _insert_pick_trade(db, "trade_1", 2, 1)
    _insert_selection(repo, roster_id=1, player_id="wr_fast", pick_slot=1, round_number=1, position="WR", archetype_label="Deep Threat")
    _insert_selection(repo, roster_id=1, player_id="wr_slot", pick_slot=2, round_number=1, position="WR", archetype_label="Slot Receiver")
    _insert_selection(repo, roster_id=1, player_id="rb_pow", pick_slot=3, round_number=1, position="RB", archetype_label="Power Back")
    _insert_selection(repo, roster_id=1, player_id="wr_big", pick_slot=4, round_number=1, position="WR", archetype_label="Contested Catch WR")

    profile = RookiePickProfileEngine(db).compute_profile("league_rookie", 1)

    assert profile.show_draft_picks_tab is True
    assert len(profile.draft_selection_history) == 4


def test_compute_positional_tendency_detects_wr_heavy_manager(db) -> None:
    _seed_league(db)
    repo = RookiePickRepo(db)
    _insert_selection(repo, roster_id=1, player_id="wr_fast", pick_slot=1, round_number=1, position="WR", archetype_label="Deep Threat")
    _insert_selection(repo, roster_id=1, player_id="wr_slot", pick_slot=2, round_number=1, position="WR", archetype_label="Slot Receiver")
    _insert_selection(repo, roster_id=1, player_id="wr_big", pick_slot=3, round_number=1, position="WR", archetype_label="Contested Catch WR")
    _insert_selection(repo, roster_id=1, player_id="rb_pow", pick_slot=4, round_number=1, position="RB", archetype_label="Power Back")
    _insert_selection(repo, roster_id=2, player_id="rb_rec", pick_slot=5, round_number=1, position="RB", archetype_label="Receiving Back")
    _insert_selection(repo, roster_id=2, player_id="rb_pow", pick_slot=6, round_number=1, position="RB", archetype_label="Power Back")
    _insert_selection(repo, roster_id=2, player_id="qb_mobile", pick_slot=7, round_number=1, position="QB", archetype_label="Dual Threat QB")
    _insert_selection(repo, roster_id=2, player_id="te_move", pick_slot=8, round_number=1, position="TE", archetype_label="Move TE")

    profile = RookiePickProfileEngine(db).compute_profile("league_rookie", 1)

    assert profile.positional_tendency["WR"] > 0


def test_compute_tendency_warnings_returns_manager_tendency_warning(db) -> None:
    _seed_league(db)
    repo = RookiePickRepo(db)
    _insert_pick_trade(db, "trade_1", 2, 1)
    _insert_pick_trade(db, "trade_2", 2, 1)
    _insert_pick_trade(db, "trade_3", 2, 1)
    _insert_selection(repo, roster_id=1, player_id="wr_fast", pick_slot=1, round_number=1, position="WR", archetype_label="Deep Threat")
    _insert_selection(repo, roster_id=1, player_id="wr_slot", pick_slot=2, round_number=1, position="WR", archetype_label="Slot Receiver")
    _insert_selection(repo, roster_id=1, player_id="wr_big", pick_slot=3, round_number=1, position="WR", archetype_label="Contested Catch WR")
    _insert_selection(repo, roster_id=1, player_id="rb_pow", pick_slot=4, round_number=1, position="RB", archetype_label="Power Back")
    _insert_selection(repo, roster_id=2, player_id="rb_rec", pick_slot=5, round_number=1, position="RB", archetype_label="Receiving Back")
    _insert_selection(repo, roster_id=2, player_id="rb_pow", pick_slot=6, round_number=1, position="RB", archetype_label="Power Back")
    _insert_selection(repo, roster_id=2, player_id="qb_mobile", pick_slot=7, round_number=1, position="QB", archetype_label="Dual Threat QB")
    _insert_selection(repo, roster_id=2, player_id="te_move", pick_slot=8, round_number=1, position="TE", archetype_label="Move TE")

    engine = RookiePickProfileEngine(db)
    engine.compute_profile("league_rookie", 1)
    warnings = engine.compute_tendency_warnings("league_rookie")

    assert warnings
    assert warnings[0].warning_type == "manager_tendency"


def test_warning_type_accepts_manager_tendency() -> None:
    warning = TendencyWarning(
        warning_type="manager_tendency",
        title="Manager A targets WR early",
        description="seed",
        affected_players=[],
    )

    assert warning.warning_type == "manager_tendency"


def test_warning_type_rejects_unknown_literal() -> None:
    try:
        TendencyWarning(
            warning_type="unknown",  # type: ignore[arg-type]
            title="seed",
            description="seed",
        )
    except ValidationError:
        assert True
    else:
        raise AssertionError("ValidationError was not raised")
