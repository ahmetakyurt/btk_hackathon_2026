"""Mock OwnSite (seller storefront) API (port 9003).

This is the seller's own Shopify-like storefront. Key differences vs Trendyol/Amazon:
- No competitors (it's the seller's own channel).
- Always has buybox (`own_has_buybox = True`).
- Optional `discount_code` field on listings.
- /admin/competitor-price returns 410 Gone (no competitors to set).
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal
from typing import AsyncIterator

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from models import Base, Listing

PLATFORM_CODE = "own_site"
EXTERNAL_ID_PREFIX = "OWN"

DB_URL = os.getenv("MOCK_OWN_SITE_DB", "sqlite+aiosqlite:///./mock_own_site.db")
engine = create_async_engine(DB_URL, echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# ─── Pydantic schemas ────────────────────────────────────────────────────

class ListProductRequest(BaseModel):
    sku: str
    title: str
    description: str | None = None
    category: str | None = None
    price: Decimal
    stock: int
    discount_code: str | None = None
    keywords: list[str] = Field(default_factory=list)


class ListingResponse(BaseModel):
    external_id: str
    platform_code: str = PLATFORM_CODE
    sku: str
    title: str
    description: str | None
    category: str | None
    listed_price: Decimal
    stock: int
    discount_code: str | None
    has_buybox: bool = True
    status: str
    listing_url: str


class UpdatePriceRequest(BaseModel):
    price: Decimal


class CompetitorsResponse(BaseModel):
    external_id: str
    platform_code: str = PLATFORM_CODE
    fetched_at: datetime
    own_price: Decimal
    own_has_buybox: bool = True
    competitors: list = Field(default_factory=list)


# ─── DB helpers ──────────────────────────────────────────────────────────

async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


def _make_external_id(seq: int) -> str:
    return f"{EXTERNAL_ID_PREFIX}-{seq:06d}"


# ─── Lifespan ────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="Mock OwnSite Storefront API",
    version="0.1.0",
    description="Simulated seller storefront for OptiPrice AI.",
    lifespan=lifespan,
)


# ─── Endpoints ───────────────────────────────────────────────────────────

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "platform": PLATFORM_CODE}


def _to_listing_response(listing: Listing) -> ListingResponse:
    return ListingResponse(
        external_id=listing.external_id,
        sku=listing.sku,
        title=listing.title,
        description=listing.description,
        category=listing.category,
        listed_price=listing.price,
        stock=listing.stock,
        discount_code=listing.discount_code,
        has_buybox=True,
        status="listed",
        listing_url=f"https://mock-own-site.local/products/{listing.external_id}",
    )


@app.post("/products", response_model=ListingResponse, status_code=201)
async def list_product(
    body: ListProductRequest,
    session: AsyncSession = Depends(get_session),
) -> ListingResponse:
    count = (await session.execute(select(Listing.id))).scalars().all()
    seq = (max(count) if count else 0) + 1
    external_id = _make_external_id(seq)

    listing = Listing(
        external_id=external_id,
        sku=body.sku,
        title=body.title,
        description=body.description,
        category=body.category,
        price=body.price,
        stock=body.stock,
        discount_code=body.discount_code,
        is_published=True,
    )
    session.add(listing)
    await session.commit()
    await session.refresh(listing)
    return _to_listing_response(listing)


async def _get_listing_or_404(
    session: AsyncSession, external_id: str
) -> Listing:
    result = await session.execute(
        select(Listing).where(Listing.external_id == external_id)
    )
    listing = result.scalar_one_or_none()
    if listing is None:
        raise HTTPException(status_code=404, detail=f"Listing {external_id} not found")
    return listing


@app.get("/products/{external_id}", response_model=ListingResponse)
async def get_listing(
    external_id: str, session: AsyncSession = Depends(get_session)
) -> ListingResponse:
    listing = await _get_listing_or_404(session, external_id)
    return _to_listing_response(listing)


@app.put("/products/{external_id}/price")
async def update_price(
    external_id: str,
    body: UpdatePriceRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    listing = await _get_listing_or_404(session, external_id)
    listing.price = body.price
    await session.commit()
    return {"ok": True, "external_id": external_id, "new_price": float(body.price)}


@app.get("/products/{external_id}/competitors", response_model=CompetitorsResponse)
async def get_competitors(
    external_id: str, session: AsyncSession = Depends(get_session)
) -> CompetitorsResponse:
    listing = await _get_listing_or_404(session, external_id)
    return CompetitorsResponse(
        external_id=listing.external_id,
        fetched_at=datetime.utcnow(),
        own_price=listing.price,
    )


@app.post("/admin/competitor-price", status_code=410)
async def admin_set_competitor_price() -> dict[str, str]:
    raise HTTPException(
        status_code=410,
        detail="OwnSite has no competitors; this endpoint is intentionally disabled.",
    )
