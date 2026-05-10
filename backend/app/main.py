from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.agents.competitor_watcher import CompetitorWatcher
from app.api.agents import broadcast_log, router as agents_router
from app.api.pricing import router as pricing_router
from app.api.products import router as products_router
from app.api.simulator import router as simulator_router
from app.config import get_settings
from app.db.models import Platform
from app.db.session import SessionLocal, engine

settings = get_settings()

# ─── Platform seed data ───────────────────────────────────────────────────────

_PLATFORMS = [
    {
        "code": "trendyol",
        "display_name": "Trendyol",
        "commission_rate": Decimal("0.2000"),
        "base_url": settings.mock_trendyol_url,
        "pricing_strategy": "buybox",
        "is_active": True,
    },
    {
        "code": "amazon",
        "display_name": "Amazon",
        "commission_rate": Decimal("0.1500"),
        "base_url": settings.mock_amazon_url,
        "pricing_strategy": "logistics_balance",
        "is_active": True,
    },
    {
        "code": "own_site",
        "display_name": "Kendi Sitem",
        "commission_rate": Decimal("0.0200"),
        "base_url": settings.mock_own_site_url,
        "pricing_strategy": "profit_max",
        "is_active": True,
    },
]


async def _seed_platforms() -> None:
    """Idempotent upsert — skips rows that already exist by code."""
    async with SessionLocal() as session:
        for p in _PLATFORMS:
            stmt = (
                sqlite_insert(Platform)
                .values(**p)
                .on_conflict_do_nothing(index_elements=["code"])
            )
            await session.execute(stmt)
        await session.commit()


# ─── DB init + seed ───────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    from app.db.base import Base  # noqa: F401 — ensures all models are registered

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await _seed_platforms()

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
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products_router)
app.include_router(pricing_router)
app.include_router(agents_router)
app.include_router(simulator_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "optiprice-backend"}
