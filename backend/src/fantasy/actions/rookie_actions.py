from __future__ import annotations

from urllib.parse import quote_plus

import duckdb

from fantasy.actions.models import CommandAction
from fantasy.context.context_repo import ContextRepo
from fantasy.context.freshness_service import FreshnessService
from fantasy.rookie.models import DraftRoomResult
from fantasy.rookie.rookie_engine import RookieEngine

DRAFT_DOMAINS = ["draft_capital", "landing_spots"]


def build_rookie_actions(
    conn: duckdb.DuckDBPyConnection,
    rosters: list[dict[str, object]],
) -> list[CommandAction]:
    actions: list[CommandAction] = []
    freshness = FreshnessService(ContextRepo(conn))
    engine = RookieEngine(conn)
    for roster in rosters:
        league_id = str(roster["league_id"])
        roster_id = int(roster["roster_id"])
        slot = _active_draft_slot(conn, league_id, roster_id)
        if slot is None:
            continue
        pick_slot, status = slot
        result = engine.compute_draft_room(league_id, pick_slot)
        actions.append(
            _rookie_action(
                freshness=freshness,
                league_id=league_id,
                league_name=_league_name(conn, league_id),
                roster_id=roster_id,
                status=status,
                result=result,
            )
        )
    return actions


def _active_draft_slot(
    conn: duckdb.DuckDBPyConnection,
    league_id: str,
    roster_id: int,
) -> tuple[int, str] | None:
    row = conn.execute(
        """
        SELECT confirmed_slot, status
        FROM draft_slots
        WHERE league_id = ?
          AND roster_id = ?
          AND confirmed_slot IS NOT NULL
          AND lower(coalesce(status, '')) IN ('pre_draft', 'drafting')
        ORDER BY season DESC, draft_id DESC
        LIMIT 1
        """,
        [league_id, roster_id],
    ).fetchone()
    if row is None:
        return None
    return int(row[0]), str(row[1] or "")


def _rookie_action(
    *,
    freshness: FreshnessService,
    league_id: str,
    league_name: str,
    roster_id: int,
    status: str,
    result: DraftRoomResult,
) -> CommandAction:
    stale_domains = [
        tag.domain
        for tag in freshness.get_tags(league_id, DRAFT_DOMAINS)
        if tag.is_stale
    ]
    return CommandAction(
        id=f"rookie:{league_id}:{roster_id}:{result.pick_slot}",
        league_id=league_id,
        roster_id=roster_id,
        category="rookie_pick",
        priority_rank=result.pick_slot,
        urgency="today" if status == "drafting" else "this_week",
        confidence=_confidence(result),
        headline=f"{league_name}: {result.trade_verdict.label} at {result.pick_slot_display}",
        recommended_action=_recommended_action(result),
        acceptable_price=_acceptable_price(result),
        timing="On the clock if drafting now; otherwise line up the deal before your pick.",
        why_now=_why_now(result),
        risk_if_wrong=(
            "Wrong if the room takes a different tier before your slot or fresh "
            "draft-capital/landing-spot data changes the board."
        ),
        evidence=_evidence(result),
        cta_label="Open Draft Room",
        cta_destination=(
            f"/draft-room?leagueId={quote_plus(league_id)}&pickSlot={result.pick_slot}"
        ),
        stale_domains=stale_domains,
    )


def _confidence(result: DraftRoomResult) -> str:
    best = result.best_in_abstract
    if best is None:
        return "LOW"
    if result.trade_verdict.verdict == "use" and best.tier_number <= 2:
        return "HIGH"
    if best.tier_number <= 3:
        return "MEDIUM"
    return "LOW"


def _recommended_action(result: DraftRoomResult) -> str:
    best = result.best_in_abstract
    if result.trade_verdict.verdict == "use" and best is not None:
        return f"Use {result.pick_slot_display} on {best.full_name} if available."
    if result.trade_back_line:
        return f"Shop {result.pick_slot_display}; {result.trade_back_line}"
    return f"Shop {result.pick_slot_display}; {result.trade_verdict.reasoning}"


def _acceptable_price(result: DraftRoomResult) -> str:
    best = result.best_in_abstract
    if result.trade_back_line:
        return result.trade_back_line
    if best is not None:
        return f"Use the pick on {best.full_name}; only trade out for a clear tier-overpay."
    return "Trade back unless the room lets a higher-tier player fall."


def _why_now(result: DraftRoomResult) -> str:
    if result.trade_back_line:
        return f"{result.trade_verdict.reasoning} {result.trade_back_line}"
    return result.trade_verdict.reasoning


def _evidence(result: DraftRoomResult) -> list[str]:
    evidence: list[str] = []
    best = result.best_in_abstract
    if best is not None:
        evidence.append(f"Best player: {best.full_name} ({best.position})")
        if best.draft_action:
            evidence.append(f"Draft action: {best.draft_action}")
    if result.expected_available_tier:
        evidence.append(f"Expected tier: {result.expected_available_tier}")
    if result.avoid_at_cost:
        evidence.append("Avoid at cost: " + ", ".join(result.avoid_at_cost[:3]))
    return evidence


def _league_name(conn: duckdb.DuckDBPyConnection, league_id: str) -> str:
    row = conn.execute(
        """
        SELECT name
        FROM leagues
        WHERE league_id = ?
        LIMIT 1
        """,
        [league_id],
    ).fetchone()
    return str(row[0]) if row and row[0] else league_id
