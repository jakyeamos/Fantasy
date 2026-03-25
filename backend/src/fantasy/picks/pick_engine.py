from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

import duckdb

from fantasy.picks.constants import (
    CALENDAR_TIMING_MULTIPLIERS,
    CLASS_STRENGTH_WEIGHT,
    DEMAND_FACTOR_MAX_PREMIUM,
    EARLY_PICK_SLOT_THRESHOLD,
    FUTURE_YEAR_DISCOUNT_RATE,
    MAX_REBUILDER_PREMIUM,
    NEAR_PEAK_MONTHS,
    NEUTRAL_REBUILDER_RATIO,
    NonPlayoffOrderBasis,
    PlayoffOrdering,
    SEASON_MIDPOINT_THRESHOLD,
    SLOT_VALUE_DECAY_EXPONENT,
    FIRST_ROUND_BASE_VALUE,
    TOTAL_SEASON_GAMES,
    TRENDING_DOWN_THRESHOLD,
    TRENDING_WINDOW,
)
from fantasy.picks.models import (
    LeagueDraftOrderRule,
    LeaguePickContext,
    PickValue,
    PickValuationContext,
    TeamStandingsRow,
    TimingLabel,
)
from fantasy.picks.pick_repo import PickRepo
from fantasy.trade.models import TradeAsset

_RULE_UNSET = object()


def sigmoid(x: float, k: float, center: float) -> float:
    import math

    return 1.0 / (1.0 + math.exp(-k * (x - center)))


def expected_draft_slot_inverse(win_pct: float, remaining_games: int, league_size: int) -> float:
    league_size = max(2, league_size)
    if remaining_games <= 0:
        slot = round(win_pct * (league_size - 1)) + 1
        return float(max(1, min(league_size, slot)))

    games_played = max(0, TOTAL_SEASON_GAMES - remaining_games)
    regressed_win_pct = (
        (win_pct * games_played + 0.5 * remaining_games) / max(TOTAL_SEASON_GAMES, 1)
    )
    slot = round(regressed_win_pct * (league_size - 1)) + 1
    return float(max(1, min(league_size, slot)))


def expected_draft_slot_max_pf(
    max_pf_slots: dict[int, int],
    roster_id: int,
    league_size: int,
) -> float:
    league_size = max(2, league_size)
    return float(max_pf_slots.get(roster_id, (league_size + 1) // 2))


def expected_draft_slot(
    rule: LeagueDraftOrderRule | None,
    win_pct: float,
    remaining_games: int,
    league_size: int,
    max_pf_slots: dict[int, int] | None = None,
    roster_id: int = 0,
) -> float | None:
    if rule is None:
        return None
    if rule.non_playoff_basis == NonPlayoffOrderBasis.INVERSE_STANDINGS:
        return expected_draft_slot_inverse(win_pct, remaining_games, league_size)
    if rule.non_playoff_basis == NonPlayoffOrderBasis.MAX_POINTS_FOR:
        return expected_draft_slot_max_pf(max_pf_slots or {}, roster_id, league_size)
    return None


def slot_to_base_value(slot: float, league_size: int) -> float:
    del league_size
    normalized_slot = max(slot, 1.0)
    return FIRST_ROUND_BASE_VALUE * (1.0 / normalized_slot) ** SLOT_VALUE_DECAY_EXPONENT


def absolute_pick_slot(round_number: int, slot_in_round: float, league_size: int) -> float:
    normalized_round = max(round_number, 1)
    normalized_slot = max(1.0, min(float(league_size), slot_in_round))
    return (normalized_round - 1) * float(league_size) + normalized_slot


def ordinal(value: int) -> str:
    if 10 <= value % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"


def projected_pick_label(round_number: int, slot_in_round: float) -> str:
    rounded_slot = max(1, round(slot_in_round))
    return f"{round_number}.{str(rounded_slot).zfill(2)}"


def _build_rule_citation(rule: LeagueDraftOrderRule | None) -> str | None:
    if rule is None:
        return None

    basis_label = {
        NonPlayoffOrderBasis.INVERSE_STANDINGS: "Inverse standings",
        NonPlayoffOrderBasis.MAX_POINTS_FOR: "Max points for",
    }[rule.non_playoff_basis]
    playoff_label = {
        PlayoffOrdering.BY_FINISH: "Playoff teams by finish",
        PlayoffOrdering.BY_RECORD: "Playoff teams by record",
        PlayoffOrdering.BY_POINTS_FOR: "Playoff teams by points for",
    }[rule.playoff_ordering]
    return f"Using: {basis_label} · {playoff_label}"


def compute_rebuilder_adjustment(rebuilder_ratio: float) -> float:
    ratio = max(0.0, min(1.0, rebuilder_ratio))
    delta = ratio - NEUTRAL_REBUILDER_RATIO
    if delta >= 0:
        scale = max(1.0 - NEUTRAL_REBUILDER_RATIO, 0.01)
    else:
        scale = max(NEUTRAL_REBUILDER_RATIO, 0.01)
    return max(-MAX_REBUILDER_PREMIUM, min(MAX_REBUILDER_PREMIUM, (delta / scale) * MAX_REBUILDER_PREMIUM))


def compute_timing_rec(
    slot: float,
    standings: TeamStandingsRow,
    month: int,
    pick_round: int,
    years_out: int,
) -> TimingLabel:
    if standings.draft_in_progress:
        return TimingLabel.USE_ON_THE_CLOCK

    if (
        pick_round == 1
        and years_out == 0
        and month in NEAR_PEAK_MONTHS
        and slot <= EARLY_PICK_SLOT_THRESHOLD
    ):
        return TimingLabel.SELL_NOW

    recent_win_rate = standings.recent_wins / max(TRENDING_WINDOW, 1)
    if (
        pick_round == 1
        and years_out == 0
        and recent_win_rate < TRENDING_DOWN_THRESHOLD
        and standings.remaining_games > SEASON_MIDPOINT_THRESHOLD
    ):
        return TimingLabel.SELL_NOW

    return TimingLabel.HOLD_UNTIL_ROOKIE_FEVER


def compute_timing_reasoning(
    label: TimingLabel,
    standings: TeamStandingsRow,
    month: int,
    pick_round: int,
    slot: float,
    years_out: int,
) -> str:
    pick_label = projected_pick_label(pick_round, slot)
    if label == TimingLabel.USE_ON_THE_CLOCK:
        return f"{pick_label} is on the clock now — use it or move it immediately."

    if label == TimingLabel.SELL_NOW:
        if month in NEAR_PEAK_MONTHS:
            return (
                f"Projects around {pick_label} and the calendar is near peak rookie fever pricing, "
                "so this is the best sell window."
            )
        return (
            f"Projects around {pick_label} and the original roster has only "
            f"{standings.recent_wins} wins in the last {TRENDING_WINDOW}, so move it before the slot improves."
        )

    if years_out > 0:
        return (
            f"Future {pick_round}{ordinal(pick_round)[-2:]} projects around {pick_label}. "
            "Hold until that rookie class is closer and league demand firms up."
        )

    if pick_round > 1:
        return (
            f"Projects around {pick_label}. Later-round picks usually gain more liquidity closer to the draft "
            "than they do selling right now."
        )

    return (
        f"Projects around {pick_label}. Hold until rookie fever gets closer unless the original roster keeps sliding."
    )


class PickEngine:
    def __init__(
        self,
        conn: duckdb.DuckDBPyConnection,
        now_fn: Callable[[], datetime] | None = None,
    ):
        self._conn = conn
        self._repo = PickRepo(conn)
        self._now = now_fn or (lambda: datetime.now(timezone.utc))

    def _load_class_strength_signal(self, league_id: str) -> float:
        cached = self._repo.get_class_strength_signal(league_id)
        if cached is not None:
            return cached

        try:
            from fantasy.rookie.rookie_engine import RookieEngine

            return RookieEngine(self._conn).compute_class_strength(league_id)
        except Exception:
            return 0.0

    def _build_context(
        self,
        pick: TradeAsset,
        league_id: str,
        target_manager_id: int | None = None,
        draft_order_rule: LeagueDraftOrderRule | None | object = _RULE_UNSET,
    ) -> PickValuationContext:
        if draft_order_rule is _RULE_UNSET:
            draft_order_rule = self._repo.get_draft_order_rule(league_id)
        class_strength_signal = self._load_class_strength_signal(league_id)
        demand_factor = (
            self._repo.get_manager_demand_factor(target_manager_id, league_id)
            if target_manager_id is not None
            else 0.5
        )
        return PickValuationContext(
            pick=pick,
            league_id=league_id,
            draft_order_rule=draft_order_rule,
            class_strength_signal=class_strength_signal,
            target_manager_demand_factor=demand_factor,
        )

    def _blocked_pick_value(
        self,
        pick: TradeAsset,
        years_out: int,
    ) -> PickValue:
        return PickValue(
            pick=pick,
            base_value=0.0,
            timed_value=0.0,
            league_adjusted_value=0.0,
            demand_adjusted_value=0.0,
            expected_draft_slot=1.0,
            timing_label=TimingLabel.HOLD_UNTIL_ROOKIE_FEVER,
            timing_reasoning="Pick projections require a configured draft order rule.",
            class_strength_signal=0.0,
            years_out=years_out,
            computed_at=self._now(),
            rule_citation=None,
        )

    def _compute_with_context(
        self,
        pick: TradeAsset,
        league_id: str,
        standings: TeamStandingsRow,
        league_ctx: LeaguePickContext,
        context: PickValuationContext,
        current_season: int,
        current_month: int,
        confirmed_slot: int | None = None,
        max_pf_slots: dict[int, int] | None = None,
    ) -> PickValue:
        pick_year = int(pick.pick_year or current_season)
        years_out = max(0, pick_year - current_season)
        rule_citation = _build_rule_citation(context.draft_order_rule)

        if context.draft_order_rule is None:
            return self._blocked_pick_value(pick, years_out)

        if years_out > 0:
            slot = (league_ctx.league_size + 1) / 2
            standings = TeamStandingsRow(
                roster_id=int(pick.pick_owner_roster_id or 0),
                wins=0,
                losses=0,
                win_pct=0.5,
                remaining_games=TOTAL_SEASON_GAMES,
                recent_wins=0,
                total_games=0,
                draft_in_progress=False,
            )
        elif confirmed_slot is not None:
            slot = float(confirmed_slot)
        else:
            slot = expected_draft_slot(
                rule=context.draft_order_rule,
                win_pct=standings.win_pct,
                remaining_games=standings.remaining_games,
                league_size=league_ctx.league_size,
                max_pf_slots=max_pf_slots,
                roster_id=int(pick.pick_owner_roster_id or standings.roster_id),
            )
            if slot is None:
                return self._blocked_pick_value(pick, years_out)

        absolute_slot = absolute_pick_slot(
            int(pick.pick_round or 1),
            slot,
            league_ctx.league_size,
        )
        base_value = slot_to_base_value(absolute_slot, league_ctx.league_size)
        if years_out > 0:
            base_value *= FUTURE_YEAR_DISCOUNT_RATE ** years_out

        calendar_mult = CALENDAR_TIMING_MULTIPLIERS.get(current_month, 1.0)
        timed_value = base_value * calendar_mult
        class_adjusted_value = timed_value * (1 + CLASS_STRENGTH_WEIGHT * context.class_strength_signal)
        rebuilder_adjustment = compute_rebuilder_adjustment(league_ctx.rebuilder_ratio)
        league_adjusted_value = class_adjusted_value * (1 + rebuilder_adjustment)

        demand_premium = DEMAND_FACTOR_MAX_PREMIUM * (context.target_manager_demand_factor - 0.5) * 2
        demand_adjusted_value = league_adjusted_value * (1 + demand_premium)

        timing_label = compute_timing_rec(
            slot,
            standings,
            current_month,
            int(pick.pick_round or 1),
            years_out,
        )
        timing_reasoning = compute_timing_reasoning(
            timing_label,
            standings,
            current_month,
            int(pick.pick_round or 1),
            slot,
            years_out,
        )

        return PickValue(
            pick=pick,
            base_value=round(base_value, 2),
            timed_value=round(timed_value, 2),
            league_adjusted_value=round(league_adjusted_value, 2),
            demand_adjusted_value=round(demand_adjusted_value, 2),
            expected_draft_slot=round(slot, 2),
            timing_label=timing_label,
            timing_reasoning=timing_reasoning,
            class_strength_signal=round(context.class_strength_signal, 4),
            years_out=years_out,
            computed_at=self._now(),
            rule_citation=rule_citation,
        )

    def compute(
        self,
        pick: TradeAsset,
        league_id: str,
        target_manager_id: int | None = None,
    ) -> PickValue:
        current_time = self._now()
        league_ctx = self._repo.get_league_pick_context(league_id)
        current_season = self._repo.get_current_season(league_id)
        draft_order_rule = self._repo.get_draft_order_rule(league_id)
        max_pf_slots = (
            self._repo.get_max_pf_slots(league_id)
            if draft_order_rule is not None
            and draft_order_rule.non_playoff_basis == NonPlayoffOrderBasis.MAX_POINTS_FOR
            else None
        )
        context = self._build_context(
            pick,
            league_id,
            target_manager_id,
            draft_order_rule=draft_order_rule,
        )
        owner_roster_id = int(pick.pick_owner_roster_id or 0)
        standings = self._repo.get_standings(owner_roster_id, league_id)
        confirmed_slot = self._repo.get_confirmed_slot(
            league_id, owner_roster_id, int(pick.pick_year or current_season)
        )
        return self._compute_with_context(
            pick=pick,
            league_id=league_id,
            standings=standings,
            league_ctx=league_ctx,
            context=context,
            current_season=current_season,
            current_month=current_time.month,
            confirmed_slot=confirmed_slot,
            max_pf_slots=max_pf_slots,
        )

    def compute_batch(
        self,
        picks: list[TradeAsset],
        league_id: str,
        target_manager_id: int | None = None,
    ) -> list[PickValue]:
        if not picks:
            return []

        current_time = self._now()
        league_ctx = self._repo.get_league_pick_context(league_id)
        current_season = self._repo.get_current_season(league_id)
        draft_order_rule = self._repo.get_draft_order_rule(league_id)
        max_pf_slots = (
            self._repo.get_max_pf_slots(league_id)
            if draft_order_rule is not None
            and draft_order_rule.non_playoff_basis == NonPlayoffOrderBasis.MAX_POINTS_FOR
            else None
        )
        context_by_pick = {
            (
                int(pick.pick_owner_roster_id or 0),
                int(pick.pick_year or current_season),
                int(pick.pick_round or 0),
            ): self._build_context(
                pick,
                league_id,
                target_manager_id,
                draft_order_rule=draft_order_rule,
            )
            for pick in picks
        }
        standings_by_owner = {
            int(pick.pick_owner_roster_id or 0): self._repo.get_standings(
                int(pick.pick_owner_roster_id or 0), league_id
            )
            for pick in picks
            if int(pick.pick_year or current_season) <= current_season
        }

        results: list[PickValue] = []
        for pick in picks:
            key = (
                int(pick.pick_owner_roster_id or 0),
                int(pick.pick_year or current_season),
                int(pick.pick_round or 0),
            )
            owner_roster_id = int(pick.pick_owner_roster_id or 0)
            standings = standings_by_owner.get(
                owner_roster_id,
                TeamStandingsRow(
                    roster_id=owner_roster_id,
                    wins=0,
                    losses=0,
                    win_pct=0.5,
                    remaining_games=TOTAL_SEASON_GAMES,
                    recent_wins=0,
                    total_games=0,
                    draft_in_progress=False,
                ),
            )
            confirmed_slot = self._repo.get_confirmed_slot(
                league_id, owner_roster_id, int(pick.pick_year or current_season)
            )
            results.append(
                self._compute_with_context(
                    pick=pick,
                    league_id=league_id,
                    standings=standings,
                    league_ctx=league_ctx,
                    context=context_by_pick[key],
                    current_season=current_season,
                    current_month=current_time.month,
                    confirmed_slot=confirmed_slot,
                    max_pf_slots=max_pf_slots,
                )
            )
        return results

    def compute_capital_score(self, league_id: str, roster_id: int) -> float:
        picks = self._repo.get_all_picks(league_id, current_owner_roster_id=roster_id)
        if not picks:
            return 0.0
        values = self.compute_batch(picks, league_id)
        return round(sum(float(value.league_adjusted_value) for value in values), 2)
