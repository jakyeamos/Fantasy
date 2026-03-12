from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Response, status

from fantasy.corrections.override_service import CorrectionCreate, CorrectionResponse, OverrideService
from fantasy.routers.deps import get_read_db_conn, get_write_db_conn

router = APIRouter(prefix="/corrections", tags=["corrections"])
service = OverrideService()


@router.post("/", response_model=CorrectionResponse, status_code=status.HTTP_201_CREATED)
def create_correction(
    data: CorrectionCreate,
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> CorrectionResponse:
    return service.create_correction(conn, data)


@router.get("/{league_id}", response_model=list[CorrectionResponse])
def list_corrections(
    league_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> list[CorrectionResponse]:
    return service.list_corrections(conn, league_id)


@router.delete("/{correction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_correction(
    correction_id: int,
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> Response:
    deleted = service.delete_correction(conn, correction_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="correction_not_found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
