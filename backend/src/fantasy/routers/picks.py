from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends, HTTPException

from fantasy.picks.pick_engine import PickEngine
from fantasy.picks.pick_repo import PickRepo
from fantasy.picks.models import PickValue
from fantasy.routers.deps import get_read_db_conn, get_write_db_conn
from fantasy.trade.models import TradeAsset

router = APIRouter(prefix="/picks", tags=["picks"])


@router.get("/{league_id}", response_model=list[PickValue])
def get_pick_values(
    league_id: str,
    target_manager_id: int | None = None,
    current_owner_roster_id: int | None = None,
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> list[PickValue]:
    repo = PickRepo(conn)
    picks = repo.get_all_picks(
        league_id,
        current_owner_roster_id=current_owner_roster_id,
    )
    if not picks:
        return []
    return PickEngine(conn).compute_batch(
        picks,
        league_id,
        target_manager_id=target_manager_id,
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
