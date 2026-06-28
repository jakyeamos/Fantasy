from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fantasy.config import get_settings
from fantasy.db.connection import close_connection, get_write_connection
from fantasy.ingestion.nfl_data_loader import load_adp_baseline
from fantasy.routers import (
    actions,
    context,
    corrections,
    dashboard,
    draft_room,
    edge_radar,
    health,
    ingest,
    intelligence,
    leagues,
    opportunities,
    picks,
    portfolio,
    profiling,
    prospects,
    rookie_board,
    snapshot_diff,
    snapshots,
    startup,
    trade,
    trust,
    waiver,
    weekly,
)
from fantasy.startup_tasks import ensure_runtime_schema, maybe_run_dev_refresh

logger = logging.getLogger(__name__)


async def _background_dev_refresh(settings: object) -> None:
    conn = get_write_connection()
    try:
        await maybe_run_dev_refresh(conn, settings)
    except Exception:
        logger.exception("Background dev auto-refresh failed.")
    finally:
        close_connection(conn)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()

    # Fast blocking startup: schema migration + ADP baseline.
    conn = get_write_connection()
    try:
        ensure_runtime_schema(conn)
        loaded = load_adp_baseline(conn)
        if loaded:
            logger.info("Loaded %s ADP baseline rows.", loaded)
        else:
            logger.info(
                "ADP baseline file not found at data/adp_baseline.csv - skipping."
            )
    except Exception:
        logger.exception("Failed startup initialization.")
    finally:
        close_connection(conn)

    # Server is ready; run dev refresh in the background so requests aren't blocked.
    refresh_task: asyncio.Task | None = None
    if settings.DEV_AUTO_REFRESH:
        refresh_task = asyncio.create_task(_background_dev_refresh(settings))

    yield

    if refresh_task is not None and not refresh_task.done():
        logger.info("Waiting for background dev refresh to finish...")
        await refresh_task


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
    app.include_router(actions.router)
    app.include_router(corrections.router)
    app.include_router(health.router)
    app.include_router(intelligence.router)
    app.include_router(leagues.router)
    app.include_router(dashboard.router)
    app.include_router(snapshots.router)
    app.include_router(profiling.router)
    app.include_router(context.router)
    app.include_router(trade.router)
    app.include_router(picks.router)
    app.include_router(prospects.router)
    app.include_router(rookie_board.router)
    app.include_router(draft_room.router)
    app.include_router(snapshot_diff.router)
    app.include_router(portfolio.router)
    app.include_router(trust.router)
    app.include_router(waiver.router)
    app.include_router(weekly.router)
    app.include_router(opportunities.router)
    app.include_router(edge_radar.router)
    app.include_router(startup.router)
    return app


app = create_app()
