from __future__ import annotations

from datetime import datetime, timezone

import pytest

from fantasy.picks.constants import DraftTiebreaker, NonPlayoffOrderBasis, PlayoffOrdering
from fantasy.picks.pick_engine import (
    PickEngine,
    _build_rule_citation,
    absolute_pick_slot,
    compute_rebuilder_adjustment,
    compute_timing_reasoning,
    compute_timing_rec,
    expected_draft_slot,
    expected_draft_slot_max_pf,
    projected_pick_label,
    slot_to_base_value,
)
from fantasy.picks.models import LeagueDraftOrderRule, LeaguePickContext, TeamStandingsRow, TimingLabel
from fantasy.trade.models import TradeAsset

_TEST_RULE_UNSET = object()


class _FakeRepo:
    def __init__(
        self,
        *,
        season: int = 2026,
        class_strength: float | None = 0.0,
        draft_order_rule: LeagueDraftOrderRule | None | object = _TEST_RULE_UNSET,
        max_pf_slots: dict[int, int] | None = None,
        confirmed_slot: int | None = None,
    ):
        self.season = season
        self.class_strength = class_strength
        if draft_order_rule is _TEST_RULE_UNSET:
            self.draft_order_rule = LeagueDraftOrderRule(
                non_playoff_basis=NonPlayoffOrderBasis.INVERSE_STANDINGS,
                playoff_ordering=PlayoffOrdering.BY_FINISH,
                tiebreaker=DraftTiebreaker.POINTS_AGAINST,
            )
        else:
            self.draft_order_rule = draft_order_rule
        self.max_pf_slots = max_pf_slots or {1: 1}
        self.confirmed_slot = confirmed_slot
        self.draft_order_rule_calls = 0
        self.max_pf_slots_calls = 0
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
        return self.confirmed_slot

    def get_league_pick_context(self, league_id: str) -> LeaguePickContext:
        assert league_id == "league_x"
        return self.league_context

    def get_manager_demand_factor(self, roster_id: int, league_id: str) -> float:
        assert league_id == "league_x"
        return self.demand_by_manager.get(roster_id, 0.5)

    def get_class_strength_signal(self, league_id: str) -> float | None:
        assert league_id == "league_x"
        return self.class_strength

    def get_draft_order_rule(self, league_id: str) -> LeagueDraftOrderRule | None:
        assert league_id == "league_x"
        self.draft_order_rule_calls += 1
        return self.draft_order_rule

    def get_max_pf_slots(self, league_id: str) -> dict[int, int]:
        assert league_id == "league_x"
        self.max_pf_slots_calls += 1
        return self.max_pf_slots


def _build_engine(db, repo: _FakeRepo | None = None, *, month: int = 4) -> PickEngine:
    engine = PickEngine(
        db,
        now_fn=lambda: datetime(2026, month, 10, tzinfo=timezone.utc),
    )
    engine._repo = repo or _FakeRepo()
    return engine


def _rule(
    basis: NonPlayoffOrderBasis = NonPlayoffOrderBasis.INVERSE_STANDINGS,
    playoff_ordering: PlayoffOrdering = PlayoffOrdering.BY_FINISH,
) -> LeagueDraftOrderRule:
    return LeagueDraftOrderRule(
        non_playoff_basis=basis,
        playoff_ordering=playoff_ordering,
        tiebreaker=DraftTiebreaker.POINTS_AGAINST,
    )


@pytest.mark.parametrize(
    ("scenario", "win_pct", "remaining", "league_size", "expected_slot_range"),
    [
        ("worst_record", 0.0, 0, 12, (1, 2)),
        ("mid_record", 0.5, 0, 12, (5, 8)),
        ("best_record", 1.0, 0, 12, (11, 12)),
    ],
)
def test_regression_inverse_standings(
    scenario: str,
    win_pct: float,
    remaining: int,
    league_size: int,
    expected_slot_range: tuple[int, int],
):
    slot = expected_draft_slot(
        _rule(),
        win_pct=win_pct,
        remaining_games=remaining,
        league_size=league_size,
    )

    assert slot is not None
    assert expected_slot_range[0] <= slot <= expected_slot_range[1], (
        f"{scenario}: slot {slot} not in range {expected_slot_range}"
    )


def test_expected_draft_slot_blocked_when_rule_is_none():
    assert (
        expected_draft_slot(
            None,
            win_pct=0.0,
            remaining_games=0,
            league_size=12,
        )
        is None
    )


def test_expected_draft_slot_worst_team_is_first_pick():
    assert (
        expected_draft_slot(
            _rule(),
            win_pct=0.0,
            remaining_games=0,
            league_size=12,
        )
        == 1.0
    )


def test_expected_draft_slot_best_team_is_last_pick():
    assert (
        expected_draft_slot(
            _rule(),
            win_pct=1.0,
            remaining_games=0,
            league_size=12,
        )
        == 12.0
    )


def test_expected_draft_slot_regresses_midseason_record():
    slot = expected_draft_slot(
        _rule(),
        win_pct=0.3,
        remaining_games=7,
        league_size=12,
    )
    assert 1.0 <= slot <= 6.0


@pytest.mark.parametrize(
    ("scenario", "roster_id", "max_pf_slots", "league_size", "expected_slot"),
    [
        ("lowest_pf_gets_pick_1", 1, {1: 1, 2: 3, 3: 2}, 3, 1),
        ("highest_pf_gets_last", 2, {1: 1, 2: 3, 3: 2}, 3, 3),
        ("mid_pf_gets_mid", 3, {1: 1, 2: 3, 3: 2}, 3, 2),
    ],
)
def test_regression_max_pf(
    scenario: str,
    roster_id: int,
    max_pf_slots: dict[int, int],
    league_size: int,
    expected_slot: int,
):
    rule = _rule(NonPlayoffOrderBasis.MAX_POINTS_FOR)
    slot = expected_draft_slot(
        rule=rule,
        win_pct=0.0,
        remaining_games=0,
        league_size=league_size,
        max_pf_slots=max_pf_slots,
        roster_id=roster_id,
    )

    assert slot == float(expected_slot), f"{scenario}: got {slot}, expected {expected_slot}"


def test_expected_draft_slot_max_pf_uses_precomputed_slots():
    assert expected_draft_slot_max_pf({1: 1, 2: 3, 3: 2}, roster_id=1, league_size=3) == 1.0
    assert expected_draft_slot_max_pf({1: 3, 2: 1, 3: 2}, roster_id=2, league_size=3) == 1.0


def test_build_rule_citation_none_returns_none():
    assert _build_rule_citation(None) is None


@pytest.mark.parametrize(
    ("basis", "playoff_ordering", "expected"),
    [
        (
            NonPlayoffOrderBasis.INVERSE_STANDINGS,
            PlayoffOrdering.BY_FINISH,
            "Using: Inverse standings · Playoff teams by finish",
        ),
        (
            NonPlayoffOrderBasis.INVERSE_STANDINGS,
            PlayoffOrdering.BY_RECORD,
            "Using: Inverse standings · Playoff teams by record",
        ),
        (
            NonPlayoffOrderBasis.INVERSE_STANDINGS,
            PlayoffOrdering.BY_POINTS_FOR,
            "Using: Inverse standings · Playoff teams by points for",
        ),
        (
            NonPlayoffOrderBasis.MAX_POINTS_FOR,
            PlayoffOrdering.BY_FINISH,
            "Using: Max points for · Playoff teams by finish",
        ),
        (
            NonPlayoffOrderBasis.MAX_POINTS_FOR,
            PlayoffOrdering.BY_RECORD,
            "Using: Max points for · Playoff teams by record",
        ),
        (
            NonPlayoffOrderBasis.MAX_POINTS_FOR,
            PlayoffOrdering.BY_POINTS_FOR,
            "Using: Max points for · Playoff teams by points for",
        ),
    ],
)
def test_build_rule_citation_all_six_combinations(
    basis: NonPlayoffOrderBasis,
    playoff_ordering: PlayoffOrdering,
    expected: str,
):
    assert _build_rule_citation(_rule(basis, playoff_ordering)) == expected


def test_regression_tiebreaker_rule_passthrough():
    for tiebreaker in DraftTiebreaker:
        rule = LeagueDraftOrderRule(
            non_playoff_basis=NonPlayoffOrderBasis.INVERSE_STANDINGS,
            playoff_ordering=PlayoffOrdering.BY_FINISH,
            tiebreaker=tiebreaker,
        )
        slot = expected_draft_slot(
            rule=rule,
            win_pct=0.5,
            remaining_games=0,
            league_size=12,
        )
        assert slot is not None
        assert 1.0 <= slot <= 12.0


@pytest.mark.parametrize(
    ("playoff_ordering", "expected_suffix"),
    [
        (PlayoffOrdering.BY_FINISH, "Playoff teams by finish"),
        (PlayoffOrdering.BY_RECORD, "Playoff teams by record"),
        (PlayoffOrdering.BY_POINTS_FOR, "Playoff teams by points for"),
    ],
)
def test_regression_playoff_ordering_in_citation(
    playoff_ordering: PlayoffOrdering,
    expected_suffix: str,
):
    citation = _build_rule_citation(_rule(NonPlayoffOrderBasis.INVERSE_STANDINGS, playoff_ordering))

    assert citation is not None
    assert citation.endswith(expected_suffix)


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
    assert result.rule_citation == "Using: Inverse standings · Playoff teams by finish"


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


def test_compute_returns_blocked_value_when_rule_missing(db):
    engine = _build_engine(db, repo=_FakeRepo(draft_order_rule=None), month=4)
    pick = TradeAsset(asset_type="pick", pick_owner_roster_id=1, pick_year=2026, pick_round=1)

    result = engine.compute(pick, "league_x")

    assert result.rule_citation is None
    assert result.expected_draft_slot == 1.0
    assert result.base_value == 0.0
    assert result.league_adjusted_value == 0.0
    assert result.demand_adjusted_value == 0.0


def test_compute_with_confirmed_slot_still_includes_rule_citation(db):
    engine = _build_engine(db, repo=_FakeRepo(confirmed_slot=4), month=4)
    pick = TradeAsset(asset_type="pick", pick_owner_roster_id=1, pick_year=2026, pick_round=1)

    result = engine.compute(pick, "league_x")

    assert result.expected_draft_slot == 4.0
    assert result.rule_citation == "Using: Inverse standings · Playoff teams by finish"


def test_compute_with_confirmed_slot_and_no_rule_stays_blocked(db):
    engine = _build_engine(
        db,
        repo=_FakeRepo(draft_order_rule=None, confirmed_slot=4),
        month=4,
    )
    pick = TradeAsset(asset_type="pick", pick_owner_roster_id=1, pick_year=2026, pick_round=1)

    result = engine.compute(pick, "league_x")

    assert result.rule_citation is None
    assert result.expected_draft_slot == 1.0
    assert result.league_adjusted_value == 0.0


def test_compute_batch_loads_rule_once(db):
    repo = _FakeRepo()
    engine = _build_engine(db, repo=repo, month=4)
    picks = [
        TradeAsset(asset_type="pick", pick_owner_roster_id=1, pick_year=2026, pick_round=1),
        TradeAsset(asset_type="pick", pick_owner_roster_id=1, pick_year=2027, pick_round=2),
    ]

    engine.compute_batch(picks, "league_x")

    assert repo.draft_order_rule_calls == 1
    assert repo.max_pf_slots_calls == 0


def test_compute_batch_loads_max_pf_slots_once_when_needed(db):
    repo = _FakeRepo(
        draft_order_rule=_rule(
            NonPlayoffOrderBasis.MAX_POINTS_FOR,
            PlayoffOrdering.BY_RECORD,
        ),
        max_pf_slots={1: 2},
    )
    engine = _build_engine(db, repo=repo, month=4)
    picks = [
        TradeAsset(asset_type="pick", pick_owner_roster_id=1, pick_year=2026, pick_round=1),
        TradeAsset(asset_type="pick", pick_owner_roster_id=1, pick_year=2026, pick_round=2),
    ]

    results = engine.compute_batch(picks, "league_x")

    assert repo.draft_order_rule_calls == 1
    assert repo.max_pf_slots_calls == 1
    assert all(result.rule_citation == "Using: Max points for · Playoff teams by record" for result in results)
