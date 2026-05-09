"""Mock Trendyol seller API (port 9001).

Simulates Trendyol's high-commission, buybox-driven marketplace:
- Each new listing gets 5 seeded competitors with prices in [-8%, +8%] band.
- Buybox is recomputed on every price change: lowest price wins.
- Admin endpoint lets the jury demo trigger price drops live.
"""

from __future__ import annotations

import os
import random
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

from models import Base, Competitor, Listing

PLATFORM_CODE = "trendyol"
EXTERNAL_ID_PREFIX = "TY"
COMPETITOR_COUNT = 5
COMPETITOR_NAMES = [
    "AvciStore",
    "Mavi52Mağaza",
    "TrendShop1",
    "FlashSatış",
    "İndirimDünyası",
    "PazarliKuralı",
    "BoxKargo",
]

DB_URL = os.getenv("MOCK_TRENDYOL_DB", "sqlite+aiosqlite:///./mock_trendyol.db")
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
    has_buybox: bool
    status: str
    listing_url: str


class UpdatePriceRequest(BaseModel):
    price: Decimal


class CompetitorEntry(BaseModel):
    seller_name: str
    price: Decimal
    has_buybox: bool


class CompetitorsResponse(BaseModel):
    external_id: str
    platform_code: str = PLATFORM_CODE
    fetched_at: datetime
    own_price: Decimal
    own_has_buybox: bool
    competitors: list[CompetitorEntry]


class AdminCompetitorPriceRequest(BaseModel):
    external_id: str
    seller_name: str
    price: Decimal


# ─── DB helpers ──────────────────────────────────────────────────────────

async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def _recompute_buybox(session: AsyncSession, listing: Listing) -> None:
    """Lowest price wins. Updates `has_buybox` on listing and all competitors."""
    candidates = [(listing.price, "self")] + [
        (c.price, c.seller_name) for c in listing.competitors
    ]
    winner_seller = min(candidates, key=lambda x: x[0])[1]
    listing.has_buybox = winner_seller == "self"
    for c in listing.competitors:
        c.has_buybox = c.seller_name == winner_seller


def _make_external_id(seq: int) -> str:
    return f"{EXTERNAL_ID_PREFIX}-{seq:08d}"


def _seed_competitors(listing_price: Decimal) -> list[Competitor]:
    chosen = random.sample(COMPETITOR_NAMES, COMPETITOR_COUNT)
    competitors: list[Competitor] = []
    for name in chosen:
        delta_pct = Decimal(str(random.uniform(-0.08, 0.08)))
        comp_price = (listing_price * (Decimal("1") + delta_pct)).quantize(Decimal("0.01"))
        competitors.append(Competitor(seller_name=name, price=comp_price))
    return competitors


# ─── Lifespan ────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="Mock Trendyol API",
    version="0.1.0",
    description="Simulated Trendyol seller API for OptiPrice AI.",
    lifespan=lifespan,
)


# ─── Endpoints ───────────────────────────────────────────────────────────

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "platform": PLATFORM_CODE}


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
        has_buybox=False,
    )
    listing.competitors = _seed_competitors(body.price)
    session.add(listing)
    await session.flush()
    await _recompute_buybox(session, listing)
    await session.commit()
    await session.refresh(listing)

    return ListingResponse(
        external_id=listing.external_id,
        sku=listing.sku,
        title=listing.title,
        description=listing.description,
        category=listing.category,
        listed_price=listing.price,
        stock=listing.stock,
        has_buybox=listing.has_buybox,
        status="listed",
        listing_url=f"https://mock-trendyol.local/p/{listing.external_id}",
    )


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
    return ListingResponse(
        external_id=listing.external_id,
        sku=listing.sku,
        title=listing.title,
        description=listing.description,
        category=listing.category,
        listed_price=listing.price,
        stock=listing.stock,
        has_buybox=listing.has_buybox,
        status="listed",
        listing_url=f"https://mock-trendyol.local/p/{listing.external_id}",
    )


@app.put("/products/{external_id}/price")
async def update_price(
    external_id: str,
    body: UpdatePriceRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    listing = await _get_listing_or_404(session, external_id)
    listing.price = body.price
    await _recompute_buybox(session, listing)
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
        own_has_buybox=listing.has_buybox,
        competitors=[
            CompetitorEntry(
                seller_name=c.seller_name, price=c.price, has_buybox=c.has_buybox
            )
            for c in listing.competitors
        ],
    )


@app.post("/admin/competitor-price")
async def admin_set_competitor_price(
    body: AdminCompetitorPriceRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    listing = await _get_listing_or_404(session, body.external_id)
    target = next(
        (c for c in listing.competitors if c.seller_name == body.seller_name), None
    )
    if target is None:
        raise HTTPException(
            status_code=404,
            detail=f"Competitor {body.seller_name!r} not found for {body.external_id}",
        )
    target.price = body.price
    await _recompute_buybox(session, listing)
    await session.commit()
    return {
        "ok": True,
        "external_id": body.external_id,
        "seller_name": body.seller_name,
        "new_price": float(body.price),
    }
