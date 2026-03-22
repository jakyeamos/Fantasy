from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fantasy.db.connection import get_write_connection
from fantasy.ingestion.nfl_data_loader import load_adp_baseline
from fantasy.routers import (
    corrections,
    dashboard,
    health,
    ingest,
    intelligence,
    snapshots,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
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
    app.include_router(dashboard.router)
    app.include_router(snapshots.router)
    return app


app = create_app()
