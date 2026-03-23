from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends

from fantasy.portfolio.models import PortfolioExposureResponse, RecalibrationHealth
from fantasy.portfolio.portfolio_engine import PortfolioEngine
from fantasy.portfolio.portfolio_repo import PortfolioRepo
from fantasy.routers.deps import get_read_db_conn

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/exposure", response_model=PortfolioExposureResponse)
def get_exposure(
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> PortfolioExposureResponse:
    engine = PortfolioEngine(conn)
    return PortfolioExposureResponse(
        exposure=engine.compute_exposure(),
        correlated_risk=engine.compute_correlated_risk(),
    )


@router.get("/health", response_model=RecalibrationHealth)
def get_health(
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> RecalibrationHealth:
    repo = PortfolioRepo(conn)
    return RecalibrationHealth(last_recalibrated_at=repo.get_last_recalibration())
