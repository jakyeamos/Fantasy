from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from fantasy.context.calendar_service import CalendarService
from fantasy.context.constants import CALENDAR_GUIDANCE
from fantasy.context.context_repo import ContextRepo
from fantasy.context.freshness_service import FreshnessService
from fantasy.context.models import RecommendationContext
from fantasy.picks.constants import DraftTiebreaker, NonPlayoffOrderBasis, PlayoffOrdering
from fantasy.picks.pick_engine import PickEngine
from fantasy.picks.pick_repo import PickRepo
from fantasy.picks.models import LeagueDraftOrderRule, PickValue
from fantasy.routers.deps import get_read_db_conn, get_write_db_conn
from fantasy.trade.models import TradeAsset

router = APIRouter(prefix="/picks", tags=["picks"])


class DraftOrderRuleRequest(BaseModel):
    non_playoff_basis: NonPlayoffOrderBasis
    playoff_ordering: PlayoffOrdering
    tiebreaker: DraftTiebreaker


class DraftOrderRuleResponse(BaseModel):
    league_id: str
    rule: LeagueDraftOrderRule


class PickListResponse(BaseModel):
    picks: list[PickValue]
    recommendation_context: RecommendationContext


def _build_recommendation_context(
    conn: duckdb.DuckDBPyConnection,
    league_id: str,
) -> RecommendationContext:
    repo = ContextRepo(conn)
    calendar_context = CalendarService(repo=repo).get_context(league_id)
    freshness_tags = FreshnessService(repo=repo).get_tags(
        league_id,
        ["injuries", "draft_capital"],
    )
    note = (
        CALENDAR_GUIDANCE.get((calendar_context.active_state, "pick_sell"))
        or CALENDAR_GUIDANCE.get((calendar_context.active_state, "pick_buy"))
        or CALENDAR_GUIDANCE.get((calendar_context.active_state, "general"))
    )
    return RecommendationContext(
        calendar_state=calendar_context.active_state,
        freshness_tags=[tag for tag in freshness_tags if tag.is_stale],
        calendar_note=note,
    )


@router.get("/{league_id}/draft-order-rule", response_model=DraftOrderRuleResponse | None)
def get_draft_order_rule(
    league_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> DraftOrderRuleResponse | None:
    rule = PickRepo(conn).get_draft_order_rule(league_id)
    if rule is None:
        return None
    return DraftOrderRuleResponse(league_id=league_id, rule=rule)


@router.put("/{league_id}/draft-order-rule", response_model=DraftOrderRuleResponse)
def save_draft_order_rule(
    league_id: str,
    body: DraftOrderRuleRequest,
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> DraftOrderRuleResponse:
    rule = LeagueDraftOrderRule(**body.model_dump())
    PickRepo(conn).save_draft_order_rule(league_id, rule)
    return DraftOrderRuleResponse(league_id=league_id, rule=rule)


@router.get("/{league_id}", response_model=PickListResponse)
def get_pick_values(
    league_id: str,
    target_manager_id: int | None = None,
    current_owner_roster_id: int | None = None,
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> PickListResponse:
    repo = PickRepo(conn)
    picks = repo.get_all_picks(
        league_id,
        current_owner_roster_id=current_owner_roster_id,
    )
    recommendation_context = _build_recommendation_context(conn, league_id)
    if not picks:
        return PickListResponse(picks=[], recommendation_context=recommendation_context)
    return PickListResponse(
        picks=PickEngine(conn).compute_batch(
            picks,
            league_id,
            target_manager_id=target_manager_id,
        ),
        recommendation_context=recommendation_context,
    )


@router.get("/{league_id}/{owner_roster_id}/{pick_year}/{pick_round}", response_model=PickValue)
def get_single_pick_value(
    league_id: str,
    owner_roster_id: int,
    pick_year: int,
    pick_round: int,
    target_manager_id: int | None = None,
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> PickValue:
    repo = PickRepo(conn)
    if not repo.has_pick(league_id, owner_roster_id, pick_year, pick_round):
        raise HTTPException(status_code=404, detail="Pick not found")

    pick = TradeAsset(
        asset_type="pick",
        pick_owner_roster_id=owner_roster_id,
        pick_year=pick_year,
        pick_round=pick_round,
        projected_slot=f"{pick_round}.mid",
    )
    return PickEngine(conn).compute(
        pick,
        league_id,
        target_manager_id=target_manager_id,
    )


@router.post("/{league_id}/recompute")
def recompute_pick_values(
    league_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> dict[str, int | str]:
    repo = PickRepo(conn)
    picks = repo.get_all_picks(league_id)
    values = PickEngine(conn).compute_batch(picks, league_id)
    repo.save_pick_values(league_id, values)
    return {"league_id": league_id, "recomputed": len(values)}
