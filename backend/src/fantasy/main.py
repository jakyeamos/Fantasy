from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fantasy.config import get_settings
from fantasy.db.connection import get_write_connection
from fantasy.ingestion.nfl_data_loader import load_adp_baseline
from fantasy.routers import (
    corrections,
    dashboard,
    draft_room,
    health,
    ingest,
    intelligence,
    leagues,
    picks,
    portfolio,
    profiling,
    rookie_board,
    snapshot_diff,
    snapshots,
    trade,
    trust,
)
from fantasy.startup_tasks import maybe_run_dev_refresh

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    conn = get_write_connection()
    try:
        loaded = load_adp_baseline(conn)
        if loaded:
            logger.info("Loaded %s ADP baseline rows.", loaded)
        else:
            logger.info(
                "ADP baseline file not found at data/adp_baseline.csv - skipping."
            )
    except Exception:
        logger.exception("Failed ADP baseline load during startup.")
    try:
        await maybe_run_dev_refresh(conn, settings)
    except Exception:
        logger.exception("Failed dev auto-refresh during startup.")
    finally:
        conn.close()

    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Fantasy Backend", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(ingest.router)
    app.include_router(corrections.router)
    app.include_router(health.router)
    app.include_router(intelligence.router)
    app.include_router(leagues.router)
    app.include_router(dashboard.router)
    app.include_router(snapshots.router)
    app.include_router(profiling.router)
    app.include_router(trade.router)
    app.include_router(picks.router)
    app.include_router(rookie_board.router)
    app.include_router(draft_room.router)
    app.include_router(snapshot_diff.router)
    app.include_router(portfolio.router)
    app.include_router(trust.router)
    return app


app = create_app()
