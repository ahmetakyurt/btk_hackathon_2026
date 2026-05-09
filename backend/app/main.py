from __future__ import annotations

from contextlib import asynccontextmanager
from decimal import Decimal
from typing import AsyncIterator

from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.api.pricing import router as pricing_router
from app.api.products import router as products_router
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
    yield
    await engine.dispose()


# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="OptiPrice AI — Core API",
    version="0.1.0",
    description="Multi-channel dynamic pricing & listing agent backend.",
    lifespan=lifespan,
)

app.include_router(products_router)
app.include_router(pricing_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "optiprice-backend"}
