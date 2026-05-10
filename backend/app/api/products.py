"""Products API — create a product and fan out to all active platforms."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.listing_agent import ListingAgent
from app.config import get_settings
from app.core.deps import get_optional_user_id
from app.db.models import Platform, Product, ProductPlatformStatus
from app.db.session import get_session
from app.integrations.base import IntegrationError
from app.integrations.mock_amazon import MockAmazonService
from app.integrations.mock_own_site import MockOwnSiteService
from app.integrations.mock_trendyol import MockTrendyolService
from app.integrations.schemas import ListingPayload
from app.schemas.products import PlatformStatusOut, ProductCreateRequest, ProductOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/products", tags=["products"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


# ─── Integration factory ──────────────────────────────────────────────────────

def _make_integration(platform: Platform) -> Any:
    settings = get_settings()
    if platform.code == "trendyol":
        return MockTrendyolService(base_url=str(settings.mock_trendyol_url))
    if platform.code == "amazon":
        return MockAmazonService(base_url=str(settings.mock_amazon_url))
    if platform.code == "own_site":
        return MockOwnSiteService(base_url=str(settings.mock_own_site_url))
    raise ValueError(f"Unknown platform code: {platform.code}")


# ─── Floor price helper ───────────────────────────────────────────────────────

def compute_floor_price(
    base_cost: Decimal,
    shipping_cost: Decimal,
    commission_rate: Decimal,
    min_margin: float = 0.05,
) -> Decimal:
    """Minimum price that covers cost + shipping + commission + min margin."""
    total_cost = base_cost + shipping_cost
    # floor = total_cost / (1 - commission_rate - min_margin)
    divisor = Decimal("1") - commission_rate - Decimal(str(min_margin))
    if divisor <= 0:
        return total_cost * Decimal("2")  # degenerate case: just double cost
    return (total_cost / divisor).quantize(Decimal("0.01"))


# ─── Per-platform listing task ────────────────────────────────────────────────

async def _list_on_platform(
    product: Product,
    platform: Platform,
    ai_title: str,
    ai_description: str,
    ai_keywords: list[str],
    listing_price: Decimal,
    floor_price: Decimal,
    session: AsyncSession,
) -> ProductPlatformStatus:
    integration = _make_integration(platform)
    payload = ListingPayload(
        sku=product.sku,
        title=ai_title,
        description=ai_description,
        category=product.category,
        price=listing_price,
        stock=product.stock,
        keywords=ai_keywords,
        raw_specs={k: str(v) for k, v in (product.raw_specs or {}).items()},
    )

    status_row = ProductPlatformStatus(
        product_id=product.id,
        platform_id=platform.id,
        ai_generated_title=ai_title,
        ai_generated_desc=ai_description,
        current_price=listing_price,
        floor_price=floor_price,
        ceiling_price=(listing_price * Decimal("2")).quantize(Decimal("0.01")),
        status="pending",
    )

    try:
        result = await integration.list_product(payload)
        status_row.external_id = result.external_id
        status_row.current_price = result.listed_price
        status_row.status = "listed"
    except IntegrationError as exc:
        logger.error(
            "list_on_platform failed for %s/%s: %s", platform.code, product.sku, exc
        )
        status_row.status = "error"

    return status_row


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("", response_model=ProductOut, status_code=201)
async def create_product(
    body: ProductCreateRequest,
    session: SessionDep,
    user_id: int | None = Depends(get_optional_user_id),
) -> ProductOut:
    # 1. Duplicate SKU check (scoped to user when set, global otherwise)
    sku_query = select(Product).where(Product.sku == body.sku)
    if user_id is not None:
        sku_query = sku_query.where(Product.user_id == user_id)
    existing = await session.scalar(sku_query)
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"SKU '{body.sku}' already exists")

    # 2. Persist product
    product = Product(
        sku=body.sku,
        title=body.title,
        base_cost=body.base_cost,
        shipping_cost=body.shipping_cost,
        stock=body.stock,
        category=body.category,
        raw_specs=body.raw_specs or None,
        user_id=user_id,
    )
    session.add(product)
    await session.flush()  # get product.id without committing

    # 3. Load active platforms
    platforms: list[Platform] = list(
        (await session.scalars(select(Platform).where(Platform.is_active.is_(True)))).all()
    )
    if not platforms:
        raise HTTPException(
            status_code=503,
            detail="No active platforms configured. Run platform seed first.",
        )

    # 4. Generate AI listings for all platforms
    settings = get_settings()
    agent = ListingAgent(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
        timeout=float(settings.gemini_timeout_seconds),
    )
    product_info: dict[str, Any] = {
        "sku": product.sku,
        "title": product.title,
        "category": product.category,
        "raw_specs": product.raw_specs or {},
    }
    platform_codes = [p.code for p in platforms]
    ai_listings = await agent.generate_all_platforms(platform_codes, product_info)

    # 5. Fan out to all platforms concurrently
    async def _task(platform: Platform) -> ProductPlatformStatus:
        ai = ai_listings.get(
            platform.code,
            agent._passthrough(platform.code, product_info),  # noqa: SLF001
        )
        floor = compute_floor_price(
            product.base_cost,
            product.shipping_cost,
            Decimal(str(platform.commission_rate)),
            settings.pricing_agent_min_margin,
        )
        listing_price = body.initial_price or (floor * Decimal("1.30")).quantize(Decimal("0.01"))
        return await _list_on_platform(
            product=product,
            platform=platform,
            ai_title=ai.title,
            ai_description=ai.description,
            ai_keywords=ai.keywords,
            listing_price=listing_price,
            floor_price=floor,
            session=session,
        )

    status_rows: list[ProductPlatformStatus] = list(
        await asyncio.gather(*[_task(p) for p in platforms])
    )

    for row in status_rows:
        session.add(row)

    await session.commit()
    await session.refresh(product)

    # 6. Build response (load platform relationships)
    loaded = await session.scalar(
        select(Product)
        .where(Product.id == product.id)
        .options(
            selectinload(Product.platform_statuses).selectinload(
                ProductPlatformStatus.platform
            )
        )
    )
    assert loaded is not None

    return _to_product_out(loaded)


@router.get("", response_model=list[ProductOut])
async def list_products(
    session: SessionDep,
    user_id: int | None = Depends(get_optional_user_id),
) -> list[ProductOut]:
    query = select(Product).options(
        selectinload(Product.platform_statuses).selectinload(
            ProductPlatformStatus.platform
        )
    )
    if user_id is not None:
        query = query.where(Product.user_id == user_id)
    rows = await session.scalars(query)
    return [_to_product_out(p) for p in rows.all()]


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(
    product_id: int,
    session: SessionDep,
    user_id: int | None = Depends(get_optional_user_id),
) -> ProductOut:
    product = await session.scalar(
        select(Product)
        .where(Product.id == product_id)
        .options(
            selectinload(Product.platform_statuses).selectinload(
                ProductPlatformStatus.platform
            )
        )
    )
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    if user_id is not None and product.user_id is not None and product.user_id != user_id:
        raise HTTPException(status_code=404, detail="Product not found")
    return _to_product_out(product)


# ─── Internal mapper ──────────────────────────────────────────────────────────

def _to_product_out(product: Product) -> ProductOut:
    return ProductOut(
        id=product.id,
        sku=product.sku,
        title=product.title,
        base_cost=product.base_cost,
        shipping_cost=product.shipping_cost,
        stock=product.stock,
        category=product.category,
        created_at=product.created_at,
        platform_statuses=[
            PlatformStatusOut(
                id=s.id,
                platform_code=s.platform.code,
                platform_name=s.platform.display_name,
                external_id=s.external_id,
                current_price=s.current_price,
                floor_price=s.floor_price,
                competitor_price=s.competitor_price,
                ai_generated_title=s.ai_generated_title,
                has_buybox=s.has_buybox,
                status=s.status,
            )
            for s in product.platform_statuses
        ],
    )
