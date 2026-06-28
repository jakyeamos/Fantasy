from __future__ import annotations

import duckdb

from fantasy.context.context_repo import ContextRepo
from fantasy.context.freshness_service import FreshnessService
from fantasy.lineup.lineup_repo import LineupRepo
from fantasy.lineup.models import LineupSlotScore
from fantasy.trends.models import OpportunityCta, OpportunityWeeklyFit

WeeklyFitContext = dict[str, object]


def build_weekly_lineup_contexts(
    conn: duckdb.DuckDBPyConnection,
    user_rosters: list[dict[str, object]],
) -> dict[tuple[str, int, str], WeeklyFitContext]:
    lineup_repo = LineupRepo(conn)
    freshness = FreshnessService(ContextRepo(conn))
    contexts: dict[tuple[str, int, str], WeeklyFitContext] = {}
    for roster in user_rosters:
        league_id = str(roster["league_id"])
        roster_id = int(roster["roster_id"])
        result = lineup_repo.get_lineup_result(league_id, roster_id)
        if result is None:
            continue
        stale_domains = [
            tag.domain
            for tag in freshness.get_tags(
                league_id,
                ["usage", "stats", "schedule", "injuries"],
            )
            if tag.is_stale
        ]
        for slot in result.slot_scores:
            if not slot.below_playoff_target and not slot.below_title_target:
                continue
            contexts[(league_id, roster_id, slot.position.upper())] = {
                "slot": slot,
                "stale_domains": stale_domains,
                "is_stale": bool(stale_domains),
                "gap_to_title_target": round(slot.gap_to_title_target, 2),
            }
    return contexts


def weekly_fit_context(
    *,
    position: str,
    suggested_action: str,
    cta: OpportunityCta | None,
    weekly_contexts: dict[tuple[str, int, str], WeeklyFitContext],
) -> WeeklyFitContext | None:
    if (
        suggested_action != "buy"
        or cta is None
        or cta.league_id is None
        or cta.user_roster_id is None
    ):
        return None
    normalized_position = position.upper()
    candidates = [normalized_position]
    if normalized_position in {"RB", "WR", "TE"}:
        candidates.append("FLEX")
    for candidate in candidates:
        context = weekly_contexts.get((cta.league_id, cta.user_roster_id, candidate))
        if context is not None:
            return context
    return None


def weekly_fit_multiplier(weekly_fit: WeeklyFitContext | None) -> float:
    if weekly_fit is None:
        return 1.0
    gap = float(weekly_fit.get("gap_to_title_target") or 0.0)
    multiplier = 1.0 + min(0.75, max(0.0, gap) / 20.0)
    if weekly_fit.get("is_stale"):
        multiplier *= 0.72
    return multiplier


def weekly_fit_note(weekly_fit: WeeklyFitContext | None) -> str:
    if weekly_fit is None:
        return ""
    slot = weekly_fit.get("slot")
    if not isinstance(slot, LineupSlotScore):
        return ""
    stale = weekly_fit.get("stale_domains") or []
    stale_note = (
        f" Verify stale weekly data first: {', '.join(str(domain) for domain in stale)}."
        if stale
        else ""
    )
    return (
        f" It also solves a current {slot.position} lineup gap: "
        f"{slot.player_name} is {slot.gap_to_title_target:.1f} below the title target."
        + stale_note
    )


def weekly_fit_payload(weekly_fit: WeeklyFitContext | None) -> OpportunityWeeklyFit | None:
    if weekly_fit is None:
        return None
    slot = weekly_fit.get("slot")
    if not isinstance(slot, LineupSlotScore):
        return None
    stale_domains = [str(domain) for domain in weekly_fit.get("stale_domains") or []]
    return OpportunityWeeklyFit(
        position=slot.position,
        player_name=slot.player_name,
        gap_to_title_target=round(slot.gap_to_title_target, 2),
        is_stale=bool(stale_domains),
        stale_domains=stale_domains,
    )
