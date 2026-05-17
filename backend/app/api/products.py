"""Products API — create a product and fan out to all active platforms."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.listing_agent import ListingAgent
from app.config import get_settings
from app.core.deps import get_current_user_id, get_optional_user_id
from app.db.models import Platform, PlatformConnection, PricingAgentLog, Product, ProductPlatformStatus
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


async def _refresh_own_site_market_ref(product_id: int, session: AsyncSession) -> None:
    """Set own_site's competitor_price to the mean of sibling Trendyol/Amazon current_price.

    Called right after listing/retry so own_site has a Pazar Ref. immediately,
    without waiting for CompetitorWatcher's next tick.
    """
    rows = list(
        (
            await session.scalars(
                select(ProductPlatformStatus)
                .where(
                    ProductPlatformStatus.product_id == product_id,
                    ProductPlatformStatus.status == "listed",
                )
                .options(selectinload(ProductPlatformStatus.platform))
            )
        ).all()
    )
    sibling_prices = [
        Decimal(str(r.current_price))
        for r in rows
        if r.platform.code in ("trendyol", "amazon") and r.current_price is not None
    ]
    own_site_rows = [r for r in rows if r.platform.code == "own_site"]
    if not own_site_rows or not sibling_prices:
        return
    mean = (sum(sibling_prices, Decimal("0")) / Decimal(len(sibling_prices))).quantize(Decimal("0.01"))
    for r in own_site_rows:
        r.competitor_price = mean
        r.has_buybox = True


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
        status_row._error_message = str(exc)  # transient, surfaced via PlatformStatusOut
    except Exception as exc:
        logger.exception(
            "list_on_platform unexpected error for %s/%s", platform.code, product.sku
        )
        status_row.status = "error"
        status_row._error_message = f"{type(exc).__name__}: {exc}"

    return status_row


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("", response_model=ProductOut, status_code=201)
async def create_product(
    body: ProductCreateRequest,
    session: SessionDep,
    user_id: int = Depends(get_current_user_id),
) -> ProductOut:
    # 1. Duplicate SKU check — global because DB has UNIQUE(sku) constraint.
    existing = await session.scalar(select(Product).where(Product.sku == body.sku))
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

    # 3. Load platforms the user has connected
    connected_platform_ids = list(
        (
            await session.scalars(
                select(PlatformConnection.platform_id).where(
                    PlatformConnection.user_id == user_id
                )
            )
        ).all()
    )
    if not connected_platform_ids:
        raise HTTPException(
            status_code=422,
            detail="Henüz hiç platform bağlantısı yok. Ürün eklemeden önce en az bir platform bağlayın.",
        )
    platforms: list[Platform] = list(
        (
            await session.scalars(
                select(Platform).where(
                    Platform.is_active.is_(True),
                    Platform.id.in_(connected_platform_ids),
                )
            )
        ).all()
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
    await _refresh_own_site_market_ref(product.id, session)
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


# ─── Retry / re-list on missing platforms ───────────────────────────────────────

class RetryResult(BaseModel):
    errors_retried: int
    new_platforms_listed: int
    total_succeeded: int
    total_failed: int
    product: ProductOut


@router.post("/{product_id}/retry", response_model=RetryResult)
async def retry_product_listing(
    product_id: int,
    session: SessionDep,
    user_id: int = Depends(get_current_user_id),
) -> RetryResult:
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
    if product.user_id is not None and product.user_id != user_id:
        raise HTTPException(status_code=404, detail="Product not found")

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

    # 1. Error statuses to retry
    error_statuses = [s for s in product.platform_statuses if s.status == "error"]

    # 2. Connected platforms that have no platform_status row at all
    connected_ids = list(
        (
            await session.scalars(
                select(PlatformConnection.platform_id).where(
                    PlatformConnection.user_id == user_id
                )
            )
        ).all()
    )
    existing_ids = {s.platform_id for s in product.platform_statuses}
    missing_platform_ids = [pid for pid in connected_ids if pid not in existing_ids]
    missing_platforms: list[Platform] = []
    if missing_platform_ids:
        missing_platforms = list(
            (
                await session.scalars(
                    select(Platform).where(
                        Platform.is_active.is_(True),
                        Platform.id.in_(missing_platform_ids),
                    )
                )
            ).all()
        )

    if not error_statuses and not missing_platforms:
        raise HTTPException(status_code=400, detail="No failed or missing platform listings to retry")

    success = 0
    failed = 0

    # Retry helper
    async def _retry_one(ps: ProductPlatformStatus) -> None:
        nonlocal success, failed
        platform = ps.platform
        integration = _make_integration(platform)
        ai = await agent.generate_listing(platform.code, product_info)
        floor = compute_floor_price(
            product.base_cost,
            product.shipping_cost,
            Decimal(str(platform.commission_rate)),
            settings.pricing_agent_min_margin,
        )
        listing_price = (floor * Decimal("1.30")).quantize(Decimal("0.01"))

        payload = ListingPayload(
            sku=product.sku,
            title=ai.title,
            description=ai.description,
            category=product.category,
            price=listing_price,
            stock=product.stock,
            keywords=ai.keywords,
            raw_specs={k: str(v) for k, v in (product.raw_specs or {}).items()},
        )
        ps.ai_generated_title = ai.title
        ps.ai_generated_desc = ai.description
        ps.current_price = listing_price
        ps.floor_price = floor
        ps.ceiling_price = (listing_price * Decimal("2")).quantize(Decimal("0.01"))

        try:
            result = await integration.list_product(payload)
            ps.external_id = result.external_id
            ps.current_price = result.listed_price
            ps.status = "listed"
            ps._error_message = None
            success += 1
        except IntegrationError as exc:
            logger.error("retry failed for %s/%s: %s", platform.code, product.sku, exc)
            ps.status = "error"
            ps._error_message = str(exc)
            failed += 1
        except Exception as exc:
            logger.exception("retry unexpected error for %s/%s", platform.code, product.sku)
            ps.status = "error"
            ps._error_message = f"{type(exc).__name__}: {exc}"
            failed += 1

    # New listing helper for missing platforms
    async def _list_new(platform: Platform) -> None:
        nonlocal success, failed
        ai = await agent.generate_listing(platform.code, product_info)
        floor = compute_floor_price(
            product.base_cost,
            product.shipping_cost,
            Decimal(str(platform.commission_rate)),
            settings.pricing_agent_min_margin,
        )
        listing_price = (floor * Decimal("1.30")).quantize(Decimal("0.01"))
        status_row = await _list_on_platform(
            product=product,
            platform=platform,
            ai_title=ai.title,
            ai_description=ai.description,
            ai_keywords=ai.keywords,
            listing_price=listing_price,
            floor_price=floor,
            session=session,
        )
        if status_row.status == "listed":
            success += 1
        else:
            failed += 1
        session.add(status_row)

    tasks = [_retry_one(ps) for ps in error_statuses]
    tasks += [_list_new(p) for p in missing_platforms]
    await asyncio.gather(*tasks)
    await session.commit()
    await _refresh_own_site_market_ref(product_id, session)
    await session.commit()

    # Re-fetch with relationships
    loaded = await session.scalar(
        select(Product)
        .where(Product.id == product_id)
        .options(
            selectinload(Product.platform_statuses).selectinload(
                ProductPlatformStatus.platform
            )
        )
    )
    assert loaded is not None

    return RetryResult(
        errors_retried=len(error_statuses),
        new_platforms_listed=len(missing_platforms),
        total_succeeded=success,
        total_failed=failed,
        product=_to_product_out(loaded),
    )


# ─── Satış Asistanı (AI Q&A) ─────────────────────────────────────────────────

class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str


_ASSISTANT_SYSTEM = (
    "Sen OptiPrice AI'ın Satış Asistanısın. "
    "Bir e-ticaret satıcısına ürün fiyatlandırma kararları hakkında Türkçe, kısa ve net yanıtlar verirsin. "
    "Yalnızca sana sağlanan ürün ve karar verilerini kullan. "
    "Spekülatif yanıt verme; veri yoksa 'Bu konuda yeterli veri yok.' de."
)


def _build_ask_context(
    product: Product,
    platform_statuses: list[ProductPlatformStatus],
    recent_logs: list[PricingAgentLog],
) -> str:
    lines = [
        f"ÜRÜN: {product.title} (SKU: {product.sku})",
        f"Maliyet: {float(product.base_cost):.2f} ₺  |  Kargo: {float(product.shipping_cost):.2f} ₺",
        "",
        "PLATFORM DURUMLARI:",
    ]
    for ps in platform_statuses:
        platform_name = ps.platform.display_name if ps.platform else ps.platform_id
        lines.append(
            f"  • {platform_name}: fiyat={float(ps.current_price):.2f} ₺" if ps.current_price else f"  • {platform_name}: listelenmedi"
        )
        if ps.floor_price:
            lines.append(f"    taban={float(ps.floor_price):.2f} ₺")
        if ps.competitor_price:
            lines.append(f"    rakip={float(ps.competitor_price):.2f} ₺")
        lines.append(f"    buybox={'Bizde' if ps.has_buybox else 'Rakipte'}")

    if recent_logs:
        lines += ["", "SON AJAN KARARLARI (en yeni önce):"]
        for log in recent_logs[:5]:
            pps = log.product_platform
            platform_code = pps.platform.code if pps and pps.platform else "?"
            price_change = ""
            if log.old_price is not None and log.new_price is not None:
                price_change = f" | {float(log.old_price):.2f} → {float(log.new_price):.2f} ₺"
            lines.append(
                f"  • [{platform_code}] {log.decision}{price_change} — {log.reasoning or 'gerekçe yok'}"
            )

    return "\n".join(lines)


@router.post("/{product_id}/ask", response_model=AskResponse)
async def ask_sales_assistant(
    product_id: int,
    body: AskRequest,
    session: SessionDep,
    user_id: int | None = Depends(get_optional_user_id),
) -> AskResponse:
    """Natural language Q&A about a product's pricing decisions (powered by Gemini)."""
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

    # Fetch last 10 pricing logs across all platform statuses
    pps_ids = [ps.id for ps in product.platform_statuses]
    recent_logs: list[PricingAgentLog] = []
    if pps_ids:
        rows = await session.scalars(
            select(PricingAgentLog)
            .where(PricingAgentLog.product_platform_id.in_(pps_ids))
            .order_by(PricingAgentLog.created_at.desc())
            .limit(10)
            .options(
                selectinload(PricingAgentLog.product_platform).selectinload(
                    ProductPlatformStatus.platform
                )
            )
        )
        recent_logs = list(rows.all())

    context = _build_ask_context(product, list(product.platform_statuses), recent_logs)
    prompt = f"{context}\n\nKULLANICI SORUSU: {body.question}"

    settings = get_settings()
    from app.core.gemini_client import build_genai_client
    client = build_genai_client()
    if client is None:
        return AskResponse(answer="Gemini API anahtarı yapılandırılmamış. Lütfen yöneticiyle iletişime geçin.")

    try:
        from google.genai import types

        def _call() -> str:
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[types.Part(text=_ASSISTANT_SYSTEM + "\n\n" + prompt)],
                    )
                ],
                config=types.GenerateContentConfig(temperature=0.3),
            )
            return response.text or "Yanıt üretilemedi."

        answer = await asyncio.wait_for(
            asyncio.to_thread(_call),
            timeout=float(settings.gemini_timeout_seconds),
        )
        return AskResponse(answer=answer)

    except TimeoutError:
        return AskResponse(answer="Yanıt zaman aşımına uğradı. Lütfen tekrar deneyin.")
    except Exception as exc:
        logger.error("SalesAssistant Gemini error: %s", exc)
        return AskResponse(answer="Bir hata oluştu. Lütfen tekrar deneyin.")


# ─── Internal mapper ──────────────────────────────────────────────────────────

def _to_product_out(product: Product) -> ProductOut:
    return ProductOut(
        id=product.id,
        sku=product.sku,
        title=product.title,
        base_cost=float(product.base_cost),
        shipping_cost=float(product.shipping_cost),
        stock=product.stock,
        category=product.category,
        created_at=product.created_at,
        platform_statuses=[
            PlatformStatusOut(
                id=s.id,
                platform_code=s.platform.code,
                platform_name=s.platform.display_name,
                external_id=s.external_id,
                current_price=float(s.current_price) if s.current_price is not None else None,
                floor_price=float(s.floor_price) if s.floor_price is not None else None,
                competitor_price=float(s.competitor_price) if s.competitor_price is not None else None,
                ai_generated_title=s.ai_generated_title,
                has_buybox=s.has_buybox,
                status=s.status,
                error_message=getattr(s, "_error_message", None),
                requires_approval=s.requires_approval,
                last_confidence_score=s.last_confidence_score,
            )
            for s in product.platform_statuses
        ],
    )
