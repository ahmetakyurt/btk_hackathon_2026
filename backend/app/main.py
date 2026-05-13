from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.agents.competitor_watcher import CompetitorWatcher
from app.api.agents import broadcast_log, router as agents_router
from app.api.auth import router as auth_router
from app.api.analytics import router as analytics_router
from app.api.connections import router as connections_router
from app.api.demo import router as demo_router
from app.api.me import router as me_router
from app.api.pricing import router as pricing_router
from app.api.products import router as products_router
from app.api.simulator import router as simulator_router
from app.config import get_settings
from app.db.session import SessionLocal, engine

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
app.include_router(me_router)
app.include_router(analytics_router)
app.include_router(connections_router)
app.include_router(demo_router)
app.include_router(products_router)
app.include_router(pricing_router)
app.include_router(agents_router)
app.include_router(simulator_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "optiprice-backend"}


@app.get("/db-health")
async def db_health() -> dict[str, str]:
    """Smoke-test the DB connection. Returns 200 on success, 503 on failure."""
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=f"DB unreachable: {exc}") from exc


@app.get("/debug")
async def debug() -> dict[str, object]:
    """Returns sanitized config — useful to verify Railway env vars without secrets."""
    s = settings
    db_url = s.database_url
    # Show only the driver+host portion, never credentials
    try:
        from urllib.parse import urlparse
        parsed = urlparse(db_url)
        db_summary = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}{parsed.path}"
    except Exception:
        db_summary = db_url[:30] + "..."
    return {
        "db_driver": db_summary,
        "has_gemini_key": bool(s.gemini_api_key),
        "has_nextauth_secret": bool(s.nextauth_secret),
        "has_resend_key": bool(s.resend_api_key),
        "gemini_model": s.gemini_model,
        "mock_trendyol_url": s.mock_trendyol_url,
        "mock_amazon_url": s.mock_amazon_url,
        "mock_own_site_url": s.mock_own_site_url,
        "cors_origins": s.cors_allowed_origins,
    }
