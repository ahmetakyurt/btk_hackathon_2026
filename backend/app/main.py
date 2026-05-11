from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.competitor_watcher import CompetitorWatcher
from app.api.agents import broadcast_log, router as agents_router
from app.api.auth import router as auth_router
from app.api.pricing import router as pricing_router
from app.api.products import router as products_router
from app.api.simulator import router as simulator_router
from app.config import get_settings
from app.db.session import engine

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Schema source of truth: Supabase migrations. No create_all here.
    watcher = CompetitorWatcher(
        poll_interval=settings.competitor_poll_interval_seconds,
        on_log=broadcast_log,
    )
    watcher_task = asyncio.create_task(watcher.start(), name="competitor-watcher")

    yield

    watcher.stop()
    watcher_task.cancel()
    try:
        await watcher_task
    except asyncio.CancelledError:
        pass
    await engine.dispose()


# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="OptiPrice AI — Core API",
    version="0.1.0",
    description="Multi-channel dynamic pricing & listing agent backend.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_allowed_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(products_router)
app.include_router(pricing_router)
app.include_router(agents_router)
app.include_router(simulator_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "optiprice-backend"}
