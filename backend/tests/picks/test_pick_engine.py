from __future__ import annotations

from datetime import datetime, timezone

import pytest

from fantasy.picks.pick_engine import (
    PickEngine,
    absolute_pick_slot,
    compute_rebuilder_adjustment,
    compute_timing_reasoning,
    compute_timing_rec,
    expected_draft_slot,
    projected_pick_label,
    slot_to_base_value,
)
from fantasy.picks.models import LeaguePickContext, TeamStandingsRow, TimingLabel
from fantasy.trade.models import TradeAsset


class _FakeRepo:
    def __init__(self, *, season: int = 2026, class_strength: float | None = 0.0):
        self.season = season
        self.class_strength = class_strength
        self.standings = TeamStandingsRow(
            roster_id=1,
            wins=4,
            losses=10,
            win_pct=4 / 14,
            remaining_games=0,
            recent_wins=0,
            total_games=14,
            draft_in_progress=False,
        )
        self.league_context = LeaguePickContext(
            league_id="league_x",
            league_size=12,
            rebuilder_count=3,
            rebuilder_ratio=0.25,
            total_teams=12,
        )
        self.demand_by_manager = {1: 0.9, 2: 0.3}

    def get_current_season(self, league_id: str) -> int:
        assert league_id == "league_x"
        return self.season

    def get_standings(self, roster_id: int, league_id: str) -> TeamStandingsRow:
        assert league_id == "league_x"
        assert roster_id == 1
        return self.standings

    def get_confirmed_slot(self, league_id: str, roster_id: int, pick_year: int) -> int | None:
        return None

    def get_league_pick_context(self, league_id: str) -> LeaguePickContext:
        assert league_id == "league_x"
        return self.league_context

    def get_manager_demand_factor(self, roster_id: int, league_id: str) -> float:
        assert league_id == "league_x"
        return self.demand_by_manager.get(roster_id, 0.5)

    def get_class_strength_signal(self, league_id: str) -> float | None:
        assert league_id == "league_x"
        return self.class_strength


def _build_engine(db, repo: _FakeRepo | None = None, *, month: int = 4) -> PickEngine:
    engine = PickEngine(
        db,
        now_fn=lambda: datetime(2026, month, 10, tzinfo=timezone.utc),
    )
    engine._repo = repo or _FakeRepo()
    return engine


def test_expected_draft_slot_worst_team_is_first_pick():
    assert expected_draft_slot(win_pct=0.0, remaining_games=0, league_size=12) == 1.0


def test_expected_draft_slot_best_team_is_last_pick():
    assert expected_draft_slot(win_pct=1.0, remaining_games=0, league_size=12) == 12.0


def test_expected_draft_slot_regresses_midseason_record():
    slot = expected_draft_slot(win_pct=0.3, remaining_games=7, league_size=12)
    assert 1.0 <= slot <= 6.0


def test_slot_to_base_value_first_overall_is_max():
    assert slot_to_base_value(slot=1, league_size=12) == pytest.approx(100.0)


def test_slot_to_base_value_drops_across_first_round():
    assert slot_to_base_value(slot=12, league_size=12) < 100.0


def test_slot_to_base_value_second_round_is_lower():
    assert slot_to_base_value(slot=13, league_size=12) < slot_to_base_value(slot=12, league_size=12)


def test_absolute_pick_slot_offsets_later_rounds():
    assert absolute_pick_slot(round_number=2, slot_in_round=1, league_size=12) == 13.0


def test_projected_pick_label_formats_round_and_slot():
    assert projected_pick_label(round_number=2, slot_in_round=3.4) == "2.03"


def test_compute_rebuilder_adjustment_neutral_ratio_is_zero():
    assert compute_rebuilder_adjustment(rebuilder_ratio=0.25) == pytest.approx(0.0)


def test_compute_rebuilder_adjustment_more_rebuilders_is_positive():
    assert compute_rebuilder_adjustment(rebuilder_ratio=0.5) > 0.0


def test_compute_rebuilder_adjustment_no_rebuilders_is_negative():
    assert compute_rebuilder_adjustment(rebuilder_ratio=0.0) < 0.0


def test_compute_timing_rec_peak_window_returns_sell_now():
    standings = TeamStandingsRow(
        roster_id=1,
        wins=2,
        losses=10,
        win_pct=0.167,
        remaining_games=0,
        recent_wins=0,
        total_games=12,
        draft_in_progress=False,
    )
    assert (
        compute_timing_rec(
            slot=1.5,
            standings=standings,
            month=4,
            pick_round=1,
            years_out=0,
        )
        == TimingLabel.SELL_NOW
    )


def test_compute_timing_rec_regular_season_returns_hold():
    standings = TeamStandingsRow(
        roster_id=1,
        wins=6,
        losses=3,
        win_pct=0.667,
        remaining_games=5,
        recent_wins=2,
        total_games=9,
        draft_in_progress=False,
    )
    assert (
        compute_timing_rec(
            slot=8.0,
            standings=standings,
            month=9,
            pick_round=1,
            years_out=0,
        )
        == TimingLabel.HOLD_UNTIL_ROOKIE_FEVER
    )


def test_compute_timing_rec_second_round_peak_window_returns_hold():
    standings = TeamStandingsRow(
        roster_id=1,
        wins=2,
        losses=10,
        win_pct=0.167,
        remaining_games=0,
        recent_wins=0,
        total_games=12,
        draft_in_progress=False,
    )
    assert (
        compute_timing_rec(
            slot=1.5,
            standings=standings,
            month=4,
            pick_round=2,
            years_out=0,
        )
        == TimingLabel.HOLD_UNTIL_ROOKIE_FEVER
    )


def test_compute_timing_rec_draft_in_progress_returns_on_the_clock():
    standings = TeamStandingsRow(
        roster_id=1,
        wins=0,
        losses=0,
        win_pct=0.5,
        remaining_games=0,
        recent_wins=0,
        total_games=0,
        draft_in_progress=True,
    )
    assert (
        compute_timing_rec(
            slot=4.0,
            standings=standings,
            month=5,
            pick_round=1,
            years_out=0,
        )
        == TimingLabel.USE_ON_THE_CLOCK
    )


def test_compute_timing_reasoning_peak_window_mentions_rookie_fever():
    standings = TeamStandingsRow(
        roster_id=1,
        wins=0,
        losses=0,
        win_pct=0.5,
        remaining_games=0,
        recent_wins=0,
        total_games=0,
        draft_in_progress=False,
    )
    reasoning = compute_timing_reasoning(
        TimingLabel.SELL_NOW,
        standings,
        4,
        pick_round=1,
        slot=2.0,
        years_out=0,
    )
    assert "rookie fever" in reasoning.lower()
    assert "1.02" in reasoning


def test_compute_timing_reasoning_trending_down_mentions_trending_down():
    standings = TeamStandingsRow(
        roster_id=1,
        wins=1,
        losses=8,
        win_pct=0.111,
        remaining_games=5,
        recent_wins=0,
        total_games=9,
        draft_in_progress=False,
    )
    reasoning = compute_timing_reasoning(
        TimingLabel.SELL_NOW,
        standings,
        9,
        pick_round=1,
        slot=3.0,
        years_out=0,
    )
    assert "last 4" in reasoning.lower()
    assert "1.03" in reasoning


def test_compute_timing_reasoning_future_pick_mentions_future_class():
    standings = TeamStandingsRow(
        roster_id=1,
        wins=0,
        losses=0,
        win_pct=0.5,
        remaining_games=14,
        recent_wins=0,
        total_games=0,
        draft_in_progress=False,
    )
    reasoning = compute_timing_reasoning(
        TimingLabel.HOLD_UNTIL_ROOKIE_FEVER,
        standings,
        3,
        pick_round=1,
        slot=6.0,
        years_out=1,
    )
    assert "future" in reasoning.lower()
    assert "1.06" in reasoning


def test_compute_with_neutral_class_strength_keeps_timed_value_unadjusted(db):
    engine = _build_engine(db, repo=_FakeRepo(class_strength=0.0), month=4)
    pick = TradeAsset(asset_type="pick", pick_owner_roster_id=1, pick_year=2026, pick_round=1)
    result = engine.compute(pick, "league_x")
    assert result.timed_value == pytest.approx(result.base_value * 1.18, abs=0.01)


def test_compute_future_year_pick_applies_discount(db):
    engine = _build_engine(db, repo=_FakeRepo(season=2026), month=4)
    current_pick = TradeAsset(asset_type="pick", pick_owner_roster_id=1, pick_year=2026, pick_round=1)
    future_pick = TradeAsset(asset_type="pick", pick_owner_roster_id=1, pick_year=2027, pick_round=1)
    current_value = engine.compute(current_pick, "league_x")
    future_value = engine.compute(future_pick, "league_x")
    assert future_value.base_value < current_value.base_value
    assert future_value.years_out == 1


def test_compute_second_round_pick_is_less_valuable_than_first_round_pick(db):
    engine = _build_engine(db, repo=_FakeRepo(season=2026), month=4)
    first_round_pick = TradeAsset(asset_type="pick", pick_owner_roster_id=1, pick_year=2026, pick_round=1)
    second_round_pick = TradeAsset(asset_type="pick", pick_owner_roster_id=1, pick_year=2026, pick_round=2)
    first_round_value = engine.compute(first_round_pick, "league_x")
    second_round_value = engine.compute(second_round_pick, "league_x")
    assert second_round_value.base_value < first_round_value.base_value
    assert second_round_value.timing_label == TimingLabel.HOLD_UNTIL_ROOKIE_FEVER


def test_missing_manager_data_falls_back_to_neutral_demand(db):
    repo = _FakeRepo()
    repo.demand_by_manager = {}
    engine = _build_engine(db, repo=repo, month=4)
    pick = TradeAsset(asset_type="pick", pick_owner_roster_id=1, pick_year=2026, pick_round=1)
    result = engine.compute(pick, "league_x", target_manager_id=99)
    assert result.demand_adjusted_value == pytest.approx(result.league_adjusted_value, abs=0.01)


def test_compute_batch_returns_one_value_per_pick(db):
    engine = _build_engine(db, month=4)
    picks = [
        TradeAsset(asset_type="pick", pick_owner_roster_id=1, pick_year=2026, pick_round=1),
        TradeAsset(asset_type="pick", pick_owner_roster_id=1, pick_year=2027, pick_round=2),
    ]
    values = engine.compute_batch(picks, "league_x")
    assert len(values) == 2
    assert all(value.pick.asset_type == "pick" for value in values)
