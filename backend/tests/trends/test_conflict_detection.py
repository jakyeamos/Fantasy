from fantasy.trends.opportunity_engine import OpportunityEngine, is_conflict
from fantasy.trends.trend_repo import TrendRepo
from fantasy.trends.constants import COMPONENT_COLS


class _StubCalendarService:
    def active_state(self, _league_id: str) -> str:
        return "early_season"


def _components(score: float) -> dict[str, float]:
    values = {column: score for column in COMPONENT_COLS}
    values["comp_fragility"] = max(0.0, min(1.0, 1.0 - score))
    return values


def _seed_minimal_feed(conn) -> None:
    conn.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions, settings_blob, superflex, tep, ppr
        )
        VALUES ('league_a', 'League A', '2025', '{}', '[]', '{}', FALSE, FALSE, 0.5)
        """
    )
    conn.execute(
        """
        INSERT INTO rosters (
            id, league_id, roster_id, owner_id, owner_display_name, starters, players, reserve, taxi
        )
        VALUES
            (1, 'league_a', 1, 'user_self', 'user_self', '[]', '[]', '[]', '[]'),
            (2, 'league_a', 2, 'user_other', 'user_other', '[]', '[]', '[]', '[]')
        """
    )


def test_conflict_buy_low_will_fall():
    assert is_conflict("buy_low", "will_fall") is True


def test_no_conflict_buy_low_will_rise():
    assert is_conflict("buy_low", "will_rise") is False


def test_conflict_sell_high_will_rise():
    assert is_conflict("sell_high", "will_rise") is True


def test_conflict_hold_despite_weak_market_will_fall():
    assert is_conflict("hold_despite_weak_market", "will_fall") is True


def test_conflict_explanation_populated(db):
    _seed_minimal_feed(db)
    db.execute(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES ('player_conflict', 'Player Conflict', 'WR', 'X', 29, '{}')
        """
    )
    db.execute(
        """
        INSERT INTO player_adp_baseline (player_id, player_name, position, adp, adp_source)
        VALUES ('player_conflict', 'Player Conflict', 'WR', 120.0, 'test')
        """
    )
    repo = TrendRepo(db)
    repo.write_trend_row(
        player_id="player_conflict",
        season=2023,
        trend_label=None,
        confidence=None,
        delta_magnitude=0.0,
        adp_delta=None,
        components=_components(0.96),
        startup_adp=96.0,
        backfilled=False,
    )
    repo.write_trend_row(
        player_id="player_conflict",
        season=2024,
        trend_label=None,
        confidence=None,
        delta_magnitude=0.0,
        adp_delta=None,
        components=_components(0.84),
        startup_adp=120.0,
        backfilled=False,
    )

    item = next(
        item
        for item in OpportunityEngine(db, calendar_service=_StubCalendarService()).build_feed()
        if item.player_id == "player_conflict"
    )

    assert item.conflict_explanation is not None
    assert len(item.conflict_explanation) > 0
