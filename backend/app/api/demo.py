"""Demo seed endpoint — creates connections and products for a new user."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.listing_agent import ListingAgent
from app.api.products import _list_on_platform, _make_integration, compute_floor_price
from app.config import get_settings
from app.core.deps import get_current_user_id
from app.db.models import Platform, PlatformConnection, Product
from app.db.session import get_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/demo", tags=["demo"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
UserIdDep = Annotated[int, Depends(get_current_user_id)]

# ─── Demo data ─────────────────────────────────────────────────────────────────

PRODUCTS: list[dict[str, Any]] = [
    {
        "sku": "SONY-WH1000XM5",
        "title": "Sony WH-1000XM5 Kablosuz Gurultu Engelleyici Kulaklik",
        "base_cost": 2800.00,
        "shipping_cost": 35.00,
        "stock": 50,
        "category": "Elektronik / Kulaklik",
        "initial_price": 4299.00,
        "raw_specs": {
            "marka": "Sony", "model": "WH-1000XM5", "baglanti": "Bluetooth 5.2",
            "pil_omru": "30 saat", "anc": "Evet", "renk": "Siyah",
        },
    },
    {
        "sku": "PHILIPS-AF9252",
        "title": "Philips Essential Airfryer XXL 6.2L Yagsiz Fritoz",
        "base_cost": 1450.00,
        "shipping_cost": 50.00,
        "stock": 30,
        "category": "Ev & Yasam / Mutfak Aletleri",
        "initial_price": 2249.00,
        "raw_specs": {
            "marka": "Philips", "model": "HD9252/91", "kapasite": "6.2 litre",
            "guc": "2000W", "kontrol": "Dijital", "renk": "Siyah",
        },
    },
    {
        "sku": "XIAOMI-MIBAND9",
        "title": "Xiaomi Mi Band 9 Akilli Bileklik - AMOLED Ekran",
        "base_cost": 450.00,
        "shipping_cost": 15.00,
        "stock": 120,
        "category": "Elektronik / Giyilebilir",
        "initial_price": 849.00,
        "raw_specs": {
            "marka": "Xiaomi", "model": "Mi Band 9", "ekran": '1.62" AMOLED',
            "su_gecirmezlik": "5 ATM", "pil_omru": "21 gun",
            "sensorler": "Nabiz, SpO2, Uyku",
        },
    },
    {
        "sku": "TEFAL-KO8501",
        "title": "Tefal Smart'n Light Elektrikli Su Isitici 1.7L",
        "base_cost": 320.00,
        "shipping_cost": 20.00,
        "stock": 80,
        "category": "Ev & Yasam / Kucuk Ev Aletleri",
        "initial_price": 599.00,
        "raw_specs": {
            "marka": "Tefal", "model": "KO850130", "kapasite": "1.7 litre",
            "guc": "2400W", "malzeme": "Cam", "garanti": "2 yil",
        },
    },
    {
        "sku": "LOGITECH-MX3S",
        "title": "Logitech MX Master 3S Kablosuz Performans Mouse",
        "base_cost": 950.00,
        "shipping_cost": 20.00,
        "stock": 60,
        "category": "Bilgisayar / Cevre Birimleri",
        "initial_price": 1699.00,
        "raw_specs": {
            "marka": "Logitech", "model": "MX Master 3S", "baglanti": "Bluetooth / USB-C",
            "dpi": "200-8000", "pil": "Sarj edilebilir", "uyumluluk": "Windows, macOS, Linux",
        },
    },
]

PLATFORM_CONNECTIONS: list[dict[str, str | None]] = [
    {"platform_code": "trendyol", "seller_id": "DEMO-12345678", "api_key": "demo-trendyol-api-key"},
    {"platform_code": "amazon", "seller_id": "DEMO-AXXXXXXXXXXXX", "api_key": "demo-amazon-mws-key"},
    {"platform_code": "own_site", "seller_id": "https://demo-store.optiprice.online", "api_key": None},
]


# ─── Response schemas ─────────────────────────────────────────────────────────

class DemoSeedResult(BaseModel):
    connections_created: int
    connections_skipped: int
    products_created: int
    products_skipped: int
    errors: list[str]


# ─── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/seed", response_model=DemoSeedResult)
async def seed_demo_data(
    session: SessionDep,
    user_id: UserIdDep,
) -> DemoSeedResult:
    connections_created = 0
    connections_skipped = 0
    products_created = 0
    products_skipped = 0
    errors: list[str] = []

    # 1. Ensure platform connections
    platforms_result = await session.execute(select(Platform).where(Platform.is_active.is_(True)))
    platforms: list[Platform] = list(platforms_result.scalars().all())
    platform_map: dict[str, Platform] = {p.code: p for p in platforms}

    existing_conns = (
        await session.execute(
            select(PlatformConnection).where(PlatformConnection.user_id == user_id)
        )
    ).scalars().all()
    existing_codes: set[str] = set()
    for ec in existing_conns:
        if ec.platform_id in platform_map:
            continue
        # Resolve platform code
        for p in platforms:
            if p.id == ec.platform_id:
                existing_codes.add(p.code)
                break

    # Re-fetch with join for reliable code lookup
    existing_codes_alt = (
        await session.execute(
            select(Platform.code)
            .join(PlatformConnection, PlatformConnection.platform_id == Platform.id)
            .where(PlatformConnection.user_id == user_id)
        )
    ).scalars().all()
    existing_codes = set(existing_codes_alt)

    for conn_data in PLATFORM_CONNECTIONS:
        code = conn_data["platform_code"]
        assert isinstance(code, str)
        if code in existing_codes:
            connections_skipped += 1
            continue
        if code not in platform_map:
            errors.append(f"Platform '{code}' not found in DB")
            continue

        conn = PlatformConnection(
            user_id=user_id,
            platform_id=platform_map[code].id,
            seller_id=str(conn_data.get("seller_id") or ""),
            api_key=str(conn_data.get("api_key") or ""),
            status="connected",
            connected_at=datetime.now(UTC).replace(tzinfo=None),
        )
        session.add(conn)
        try:
            await session.flush()
            connections_created += 1
        except IntegrityError:
            await session.rollback()
            connections_skipped += 1

    await session.commit()

    # Reload existing codes after commit
    existing_codes = set((
        await session.execute(
            select(Platform.code)
            .join(PlatformConnection, PlatformConnection.platform_id == Platform.id)
            .where(PlatformConnection.user_id == user_id)
        )
    ).scalars().all())

    if not existing_codes:
        errors.append("Henuz hic platform baglantisi yok")
        return DemoSeedResult(
            connections_created=connections_created,
            connections_skipped=connections_skipped,
            products_created=0,
            products_skipped=0,
            errors=errors,
        )

    # 2. Load ListingAgent
    settings = get_settings()
    agent = ListingAgent(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
        timeout=float(settings.gemini_timeout_seconds),
    )

    # 3. Seed products
    for p_data in PRODUCTS:
        sku = p_data["sku"]
        # Check SKU existence
        existing_prod = await session.scalar(select(Product).where(Product.sku == sku))
        if existing_prod is not None:
            products_skipped += 1
            continue

        # Create product
        product = Product(
            sku=sku,
            title=str(p_data["title"]),
            base_cost=Decimal(str(p_data["base_cost"])),
            shipping_cost=Decimal(str(p_data["shipping_cost"])),
            stock=int(p_data["stock"]),
            category=str(p_data.get("category") or ""),
            raw_specs=p_data.get("raw_specs") or {},
            user_id=user_id,
        )
        session.add(product)
        await session.flush()

        # Get connected platforms
        conn_platform_codes = list(existing_codes)
        target_platforms = [platform_map[c] for c in conn_platform_codes if c in platform_map]
        if not target_platforms:
            errors.append(f"No platforms configured for {sku}")
            continue

        # Generate AI listings
        product_info: dict[str, Any] = {
            "sku": product.sku,
            "title": product.title,
            "category": product.category,
            "raw_specs": product.raw_specs or {},
        }
        platform_codes = [p.code for p in target_platforms]
        try:
            ai_listings = await agent.generate_all_platforms(platform_codes, product_info)
        except Exception as exc:
            logger.exception("ListingAgent failed for %s", sku)
            errors.append(f"ListingAgent error for {sku}: {exc}")
            continue

        # Fan out to platforms concurrently
        async def _task(platform: Platform) -> Any:
            ai = ai_listings.get(platform.code, agent._passthrough(platform.code, product_info))
            floor = compute_floor_price(
                product.base_cost,
                product.shipping_cost,
                Decimal(str(platform.commission_rate)),
                settings.pricing_agent_min_margin,
            )
            listing_price = Decimal(str(p_data["initial_price"]))
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

        status_rows = await asyncio.gather(*[_task(p) for p in target_platforms])
        for row in status_rows:
            session.add(row)

        try:
            await session.commit()
            products_created += 1
        except IntegrityError:
            await session.rollback()
            products_skipped += 1

    return DemoSeedResult(
        connections_created=connections_created,
        connections_skipped=connections_skipped,
        products_created=products_created,
        products_skipped=products_skipped,
        errors=errors,
    )
