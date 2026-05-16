"""Combined mock platform services — Trendyol + Amazon + OwnSite on a single port.

Routes:
  /trendyol/...   → mock Trendyol seller API
  /amazon/...     → mock Amazon SP-API
  /own_site/...   → mock OwnSite storefront
  /health         → combined health check
"""

from __future__ import annotations

import os
import random
import string
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from typing import AsyncIterator

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text,
    func, select,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ═══════════════════════════════════════════════════════════════════════════════
# MODELS — each platform has its own Base + engine to avoid table name conflicts
# ═══════════════════════════════════════════════════════════════════════════════

class TyBase(DeclarativeBase):
    pass

class AzBase(DeclarativeBase):
    pass

class OsBase(DeclarativeBase):
    pass


# ── Trendyol models ──────────────────────────────────────────────────────────

class TyListing(TyBase):
    __tablename__ = "listings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    sku: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    stock: Mapped[int] = mapped_column(Integer, default=0)
    has_buybox: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    competitors: Mapped[list[TyCompetitor]] = relationship(
        back_populates="listing", cascade="all, delete-orphan", lazy="selectin"
    )


class TyCompetitor(TyBase):
    __tablename__ = "competitors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), index=True)
    seller_name: Mapped[str] = mapped_column(String(64))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    has_buybox: Mapped[bool] = mapped_column(Boolean, default=False)
    listing: Mapped[TyListing] = relationship(back_populates="competitors")


# ── Amazon models ────────────────────────────────────────────────────────────

class AzListing(AzBase):
    __tablename__ = "listings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    sku: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    fulfillment: Mapped[str] = mapped_column(String(8), default="FBM")
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    stock: Mapped[int] = mapped_column(Integer, default=0)
    has_buybox: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    competitors: Mapped[list[AzCompetitor]] = relationship(
        back_populates="listing", cascade="all, delete-orphan", lazy="selectin"
    )


class AzCompetitor(AzBase):
    __tablename__ = "competitors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), index=True)
    seller_name: Mapped[str] = mapped_column(String(64))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    has_buybox: Mapped[bool] = mapped_column(Boolean, default=False)
    listing: Mapped[AzListing] = relationship(back_populates="competitors")


# ── OwnSite models ───────────────────────────────────────────────────────────

class OsListing(OsBase):
    __tablename__ = "listings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    sku: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    stock: Mapped[int] = mapped_column(Integer, default=0)
    discount_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ═══════════════════════════════════════════════════════════════════════════════
# ENGINES + SESSION FACTORIES
# ═══════════════════════════════════════════════════════════════════════════════

ty_engine = create_async_engine(os.getenv("MOCK_TRENDYOL_DB", "sqlite+aiosqlite:///./mock_trendyol.db"), echo=False)
az_engine = create_async_engine(os.getenv("MOCK_AMAZON_DB",   "sqlite+aiosqlite:///./mock_amazon.db"),   echo=False)
os_engine = create_async_engine(os.getenv("MOCK_OWN_SITE_DB", "sqlite+aiosqlite:///./mock_own_site.db"), echo=False)

TySession = async_sessionmaker(ty_engine, class_=AsyncSession, expire_on_commit=False)
AzSession = async_sessionmaker(az_engine, class_=AsyncSession, expire_on_commit=False)
OsSession = async_sessionmaker(os_engine, class_=AsyncSession, expire_on_commit=False)


async def get_ty_session() -> AsyncIterator[AsyncSession]:
    async with TySession() as s:
        yield s

async def get_az_session() -> AsyncIterator[AsyncSession]:
    async with AzSession() as s:
        yield s

async def get_os_session() -> AsyncIterator[AsyncSession]:
    async with OsSession() as s:
        yield s


# ═══════════════════════════════════════════════════════════════════════════════
# LIFESPAN
# ═══════════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    async with ty_engine.begin() as c:
        await c.run_sync(TyBase.metadata.create_all)
    async with az_engine.begin() as c:
        await c.run_sync(AzBase.metadata.create_all)
    async with os_engine.begin() as c:
        await c.run_sync(OsBase.metadata.create_all)
    yield
    await ty_engine.dispose()
    await az_engine.dispose()
    await os_engine.dispose()


# ═══════════════════════════════════════════════════════════════════════════════
# TRENDYOL ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

TY_COMPETITOR_NAMES = ["AvciStore", "Mavi52Mağaza", "TrendShop1", "FlashSatış", "İndirimDünyası", "PazarliKuralı", "BoxKargo"]

class TyListProductRequest(BaseModel):
    sku: str
    title: str
    description: str | None = None
    category: str | None = None
    price: Decimal
    stock: int
    keywords: list[str] = Field(default_factory=list)
    raw_specs: dict[str, str] = Field(default_factory=dict)

class TyListingResponse(BaseModel):
    external_id: str
    platform_code: str = "trendyol"
    sku: str
    title: str
    description: str | None
    category: str | None
    listed_price: Decimal
    stock: int
    has_buybox: bool
    status: str
    listing_url: str

class TyUpdatePriceRequest(BaseModel):
    price: Decimal

class TyCompetitorEntry(BaseModel):
    seller_name: str
    price: Decimal
    has_buybox: bool

class TyCompetitorsResponse(BaseModel):
    external_id: str
    platform_code: str = "trendyol"
    fetched_at: datetime
    own_price: Decimal
    own_has_buybox: bool
    competitors: list[TyCompetitorEntry]

class TyAdminRequest(BaseModel):
    external_id: str
    seller_name: str
    price: Decimal


def _ty_seed_competitors(price: Decimal) -> list[TyCompetitor]:
    # Competitors start 3–25% above our listing price so we naturally win buybox
    # and the BUYBOX strategy raises our price toward theirs over time.
    # Simulator lets the jury drop competitors below us to trigger repricing.
    return [
        TyCompetitor(
            seller_name=name,
            price=(price * (Decimal("1") + Decimal(str(random.uniform(0.03, 0.25))))).quantize(Decimal("0.01")),
        )
        for name in random.sample(TY_COMPETITOR_NAMES, 5)
    ]

async def _ty_recompute_buybox(session: AsyncSession, listing: TyListing) -> None:
    candidates = [(listing.price, "self")] + [(c.price, c.seller_name) for c in listing.competitors]
    winner = min(candidates, key=lambda x: x[0])[1]
    listing.has_buybox = winner == "self"
    for c in listing.competitors:
        c.has_buybox = c.seller_name == winner

async def _ty_get_or_404(session: AsyncSession, external_id: str) -> TyListing:
    row = (await session.execute(select(TyListing).where(TyListing.external_id == external_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, f"Listing {external_id} not found")
    return row


ty_router = APIRouter(prefix="/trendyol", tags=["trendyol"])

@ty_router.get("/health")
async def ty_health() -> dict[str, str]:
    return {"status": "ok", "platform": "trendyol"}

@ty_router.post("/products", response_model=TyListingResponse, status_code=201)
async def ty_list_product(body: TyListProductRequest, session: AsyncSession = Depends(get_ty_session)) -> TyListingResponse:
    count = (await session.execute(select(TyListing.id))).scalars().all()
    seq = (max(count) if count else 0) + 1
    external_id = f"TY-{seq:08d}"
    listing = TyListing(external_id=external_id, sku=body.sku, title=body.title,
                        description=body.description, category=body.category,
                        price=body.price, stock=body.stock, has_buybox=False)
    listing.competitors = _ty_seed_competitors(body.price)
    session.add(listing)
    await session.flush()
    await _ty_recompute_buybox(session, listing)
    await session.commit()
    await session.refresh(listing)
    return TyListingResponse(external_id=listing.external_id, sku=listing.sku, title=listing.title,
                             description=listing.description, category=listing.category,
                             listed_price=listing.price, stock=listing.stock,
                             has_buybox=listing.has_buybox, status="listed",
                             listing_url=f"https://mock-trendyol.local/p/{listing.external_id}")

@ty_router.get("/products/{external_id}", response_model=TyListingResponse)
async def ty_get_listing(external_id: str, session: AsyncSession = Depends(get_ty_session)) -> TyListingResponse:
    listing = await _ty_get_or_404(session, external_id)
    return TyListingResponse(external_id=listing.external_id, sku=listing.sku, title=listing.title,
                             description=listing.description, category=listing.category,
                             listed_price=listing.price, stock=listing.stock,
                             has_buybox=listing.has_buybox, status="listed",
                             listing_url=f"https://mock-trendyol.local/p/{listing.external_id}")

@ty_router.put("/products/{external_id}/price")
async def ty_update_price(external_id: str, body: TyUpdatePriceRequest, session: AsyncSession = Depends(get_ty_session)) -> dict[str, object]:
    listing = await _ty_get_or_404(session, external_id)
    listing.price = body.price
    await _ty_recompute_buybox(session, listing)
    await session.commit()
    return {"ok": True, "external_id": external_id, "new_price": float(body.price)}

@ty_router.get("/products/{external_id}/competitors", response_model=TyCompetitorsResponse)
async def ty_get_competitors(external_id: str, session: AsyncSession = Depends(get_ty_session)) -> TyCompetitorsResponse:
    listing = await _ty_get_or_404(session, external_id)
    await _ty_recompute_buybox(session, listing)
    await session.commit()
    return TyCompetitorsResponse(external_id=listing.external_id, fetched_at=datetime.now(UTC),
                                 own_price=listing.price, own_has_buybox=listing.has_buybox,
                                 competitors=[TyCompetitorEntry(seller_name=c.seller_name, price=c.price, has_buybox=c.has_buybox)
                                              for c in listing.competitors])

@ty_router.post("/admin/competitor-price")
async def ty_admin_set_competitor_price(body: TyAdminRequest, session: AsyncSession = Depends(get_ty_session)) -> dict[str, object]:
    listing = await _ty_get_or_404(session, body.external_id)
    target = next((c for c in listing.competitors if c.seller_name == body.seller_name), None)
    if target is None:
        raise HTTPException(404, f"Competitor {body.seller_name!r} not found")
    target.price = body.price
    await _ty_recompute_buybox(session, listing)
    await session.commit()
    return {"ok": True, "external_id": body.external_id, "seller_name": body.seller_name, "new_price": float(body.price)}


# ═══════════════════════════════════════════════════════════════════════════════
# AMAZON ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

AZ_COMPETITOR_NAMES = ["PrimeSellerX", "GlobalShop", "FastShipCo", "EagleRetail", "BlueDotStore", "QuickBoxes"]

class AzListProductRequest(BaseModel):
    sku: str
    title: str
    description: str | None = None
    category: str | None = None
    price: Decimal
    stock: int
    fulfillment: str = "FBM"
    keywords: list[str] = Field(default_factory=list)
    raw_specs: dict[str, str] = Field(default_factory=dict)

class AzListingResponse(BaseModel):
    external_id: str
    platform_code: str = "amazon"
    sku: str
    title: str
    description: str | None
    category: str | None
    fulfillment: str
    listed_price: Decimal
    stock: int
    has_buybox: bool
    status: str
    listing_url: str

class AzUpdatePriceRequest(BaseModel):
    price: Decimal

class AzCompetitorEntry(BaseModel):
    seller_name: str
    price: Decimal
    has_buybox: bool

class AzCompetitorsResponse(BaseModel):
    external_id: str
    platform_code: str = "amazon"
    fetched_at: datetime
    own_price: Decimal
    own_has_buybox: bool
    competitors: list[AzCompetitorEntry]

class AzAdminRequest(BaseModel):
    external_id: str
    seller_name: str
    price: Decimal


def _az_seed_competitors(price: Decimal) -> list[AzCompetitor]:
    # Competitors start 3–20% above our listing price so we naturally win buybox.
    return [
        AzCompetitor(
            seller_name=name,
            price=(price * (Decimal("1") + Decimal(str(random.uniform(0.03, 0.20))))).quantize(Decimal("0.01")),
        )
        for name in random.sample(AZ_COMPETITOR_NAMES, 4)
    ]

async def _az_recompute_buybox(session: AsyncSession, listing: AzListing) -> None:
    candidates = [(listing.price, "self")] + [(c.price, c.seller_name) for c in listing.competitors]
    winner = min(candidates, key=lambda x: x[0])[1]
    listing.has_buybox = winner == "self"
    for c in listing.competitors:
        c.has_buybox = c.seller_name == winner

async def _az_get_or_404(session: AsyncSession, external_id: str) -> AzListing:
    row = (await session.execute(select(AzListing).where(AzListing.external_id == external_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, f"ASIN {external_id} not found")
    return row


az_router = APIRouter(prefix="/amazon", tags=["amazon"])

@az_router.get("/health")
async def az_health() -> dict[str, str]:
    return {"status": "ok", "platform": "amazon"}

@az_router.post("/products", response_model=AzListingResponse, status_code=201)
async def az_list_product(body: AzListProductRequest, session: AsyncSession = Depends(get_az_session)) -> AzListingResponse:
    if body.fulfillment not in ("FBA", "FBM"):
        raise HTTPException(400, "fulfillment must be FBA or FBM")
    for _ in range(5):
        external_id = "B0" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if not (await session.execute(select(AzListing.id).where(AzListing.external_id == external_id))).scalar_one_or_none():
            break
    else:
        raise HTTPException(500, "Could not allocate ASIN")
    listing = AzListing(external_id=external_id, sku=body.sku, title=body.title,
                        description=body.description, category=body.category,
                        fulfillment=body.fulfillment, price=body.price, stock=body.stock, has_buybox=False)
    listing.competitors = _az_seed_competitors(body.price)
    session.add(listing)
    await session.flush()
    await _az_recompute_buybox(session, listing)
    await session.commit()
    await session.refresh(listing)
    return AzListingResponse(external_id=listing.external_id, sku=listing.sku, title=listing.title,
                             description=listing.description, category=listing.category,
                             fulfillment=listing.fulfillment, listed_price=listing.price,
                             stock=listing.stock, has_buybox=listing.has_buybox, status="listed",
                             listing_url=f"https://mock-amazon.local/dp/{listing.external_id}")

@az_router.get("/products/{external_id}", response_model=AzListingResponse)
async def az_get_listing(external_id: str, session: AsyncSession = Depends(get_az_session)) -> AzListingResponse:
    listing = await _az_get_or_404(session, external_id)
    return AzListingResponse(external_id=listing.external_id, sku=listing.sku, title=listing.title,
                             description=listing.description, category=listing.category,
                             fulfillment=listing.fulfillment, listed_price=listing.price,
                             stock=listing.stock, has_buybox=listing.has_buybox, status="listed",
                             listing_url=f"https://mock-amazon.local/dp/{listing.external_id}")

@az_router.put("/products/{external_id}/price")
async def az_update_price(external_id: str, body: AzUpdatePriceRequest, session: AsyncSession = Depends(get_az_session)) -> dict[str, object]:
    listing = await _az_get_or_404(session, external_id)
    listing.price = body.price
    await _az_recompute_buybox(session, listing)
    await session.commit()
    return {"ok": True, "external_id": external_id, "new_price": float(body.price)}

@az_router.get("/products/{external_id}/competitors", response_model=AzCompetitorsResponse)
async def az_get_competitors(external_id: str, session: AsyncSession = Depends(get_az_session)) -> AzCompetitorsResponse:
    listing = await _az_get_or_404(session, external_id)
    await _az_recompute_buybox(session, listing)
    await session.commit()
    return AzCompetitorsResponse(external_id=listing.external_id, fetched_at=datetime.now(UTC),
                                 own_price=listing.price, own_has_buybox=listing.has_buybox,
                                 competitors=[AzCompetitorEntry(seller_name=c.seller_name, price=c.price, has_buybox=c.has_buybox)
                                              for c in listing.competitors])

@az_router.post("/admin/competitor-price")
async def az_admin_set_competitor_price(body: AzAdminRequest, session: AsyncSession = Depends(get_az_session)) -> dict[str, object]:
    listing = await _az_get_or_404(session, body.external_id)
    target = next((c for c in listing.competitors if c.seller_name == body.seller_name), None)
    if target is None:
        raise HTTPException(404, f"Competitor {body.seller_name!r} not found")
    target.price = body.price
    await _az_recompute_buybox(session, listing)
    await session.commit()
    return {"ok": True, "external_id": body.external_id, "seller_name": body.seller_name, "new_price": float(body.price)}


# ═══════════════════════════════════════════════════════════════════════════════
# OWN SITE ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

class OsListProductRequest(BaseModel):
    sku: str
    title: str
    description: str | None = None
    category: str | None = None
    price: Decimal
    stock: int
    discount_code: str | None = None
    keywords: list[str] = Field(default_factory=list)
    raw_specs: dict[str, str] = Field(default_factory=dict)

class OsListingResponse(BaseModel):
    external_id: str
    platform_code: str = "own_site"
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

class OsUpdatePriceRequest(BaseModel):
    price: Decimal

class OsCompetitorsResponse(BaseModel):
    external_id: str
    platform_code: str = "own_site"
    fetched_at: datetime
    own_price: Decimal
    own_has_buybox: bool = True
    competitors: list = Field(default_factory=list)


async def _os_get_or_404(session: AsyncSession, external_id: str) -> OsListing:
    row = (await session.execute(select(OsListing).where(OsListing.external_id == external_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, f"Listing {external_id} not found")
    return row


os_router = APIRouter(prefix="/own_site", tags=["own_site"])

@os_router.get("/health")
async def os_health() -> dict[str, str]:
    return {"status": "ok", "platform": "own_site"}

@os_router.post("/products", response_model=OsListingResponse, status_code=201)
async def os_list_product(body: OsListProductRequest, session: AsyncSession = Depends(get_os_session)) -> OsListingResponse:
    count = (await session.execute(select(OsListing.id))).scalars().all()
    seq = (max(count) if count else 0) + 1
    external_id = f"OWN-{seq:06d}"
    listing = OsListing(external_id=external_id, sku=body.sku, title=body.title,
                        description=body.description, category=body.category,
                        price=body.price, stock=body.stock,
                        discount_code=body.discount_code, is_published=True)
    session.add(listing)
    await session.commit()
    await session.refresh(listing)
    return OsListingResponse(external_id=listing.external_id, sku=listing.sku, title=listing.title,
                             description=listing.description, category=listing.category,
                             listed_price=listing.price, stock=listing.stock,
                             discount_code=listing.discount_code, has_buybox=True, status="listed",
                             listing_url=f"https://mock-own-site.local/products/{listing.external_id}")

@os_router.get("/products/{external_id}", response_model=OsListingResponse)
async def os_get_listing(external_id: str, session: AsyncSession = Depends(get_os_session)) -> OsListingResponse:
    listing = await _os_get_or_404(session, external_id)
    return OsListingResponse(external_id=listing.external_id, sku=listing.sku, title=listing.title,
                             description=listing.description, category=listing.category,
                             listed_price=listing.price, stock=listing.stock,
                             discount_code=listing.discount_code, has_buybox=True, status="listed",
                             listing_url=f"https://mock-own-site.local/products/{listing.external_id}")

@os_router.put("/products/{external_id}/price")
async def os_update_price(external_id: str, body: OsUpdatePriceRequest, session: AsyncSession = Depends(get_os_session)) -> dict[str, object]:
    listing = await _os_get_or_404(session, external_id)
    listing.price = body.price
    await session.commit()
    return {"ok": True, "external_id": external_id, "new_price": float(body.price)}

@os_router.get("/products/{external_id}/competitors", response_model=OsCompetitorsResponse)
async def os_get_competitors(external_id: str, session: AsyncSession = Depends(get_os_session)) -> OsCompetitorsResponse:
    listing = await _os_get_or_404(session, external_id)
    return OsCompetitorsResponse(external_id=listing.external_id, fetched_at=datetime.now(UTC), own_price=listing.price)

@os_router.post("/admin/competitor-price", status_code=410)
async def os_admin_set_competitor_price() -> dict[str, str]:
    raise HTTPException(410, "OwnSite has no competitors; this endpoint is intentionally disabled.")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="Mock Platform Services",
    version="0.1.0",
    description="Combined Trendyol + Amazon + OwnSite mock APIs for OptiPrice AI.",
    lifespan=lifespan,
)

app.include_router(ty_router)
app.include_router(az_router)
app.include_router(os_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "mock-platforms"}
