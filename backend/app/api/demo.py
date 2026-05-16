"""Demo seed endpoint — creates connections and products for a new user."""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import UTC, datetime, timedelta
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
from app.db.models import Platform, PlatformConnection, PricingAgentLog, Product, ProductPlatformStatus
from app.db.session import get_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/demo", tags=["demo"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
UserIdDep = Annotated[int, Depends(get_current_user_id)]

# ─── Demo data ─────────────────────────────────────────────────────────────────
# base_sku is suffixed with user_id at runtime to keep the global UNIQUE constraint satisfied.

PRODUCTS: list[dict[str, Any]] = [
    {
        "base_sku": "SONY-WH1000XM5",
        "title": "Sony WH-1000XM5 Kablosuz Gürültü Engelleyici Kulaklık",
        "base_cost": 2800.00,
        "shipping_cost": 35.00,
        "stock": 50,
        "category": "Elektronik / Kulaklık",
        "initial_price": 4299.00,
        "raw_specs": {
            "marka": "Sony", "model": "WH-1000XM5", "bağlantı": "Bluetooth 5.2",
            "pil_ömrü": "30 saat", "anc": "Evet", "renk": "Siyah",
        },
    },
    {
        "base_sku": "PHILIPS-AF9252",
        "title": "Philips Essential Airfryer XXL 6.2L Yağsız Fritöz",
        "base_cost": 1450.00,
        "shipping_cost": 50.00,
        "stock": 30,
        "category": "Ev & Yaşam / Mutfak Aletleri",
        "initial_price": 2249.00,
        "raw_specs": {
            "marka": "Philips", "model": "HD9252/91", "kapasite": "6.2 litre",
            "güç": "2000W", "kontrol": "Dijital", "renk": "Siyah",
        },
    },
    {
        "base_sku": "XIAOMI-MIBAND9",
        "title": "Xiaomi Mi Band 9 Akıllı Bileklik - AMOLED Ekran",
        "base_cost": 450.00,
        "shipping_cost": 15.00,
        "stock": 120,
        "category": "Elektronik / Giyilebilir",
        "initial_price": 849.00,
        "raw_specs": {
            "marka": "Xiaomi", "model": "Mi Band 9", "ekran": '1.62" AMOLED',
            "su_geçirmezlik": "5 ATM", "pil_ömrü": "21 gün",
            "sensörler": "Nabız, SpO2, Uyku",
        },
    },
    {
        "base_sku": "TEFAL-KO8501",
        "title": "Tefal Smart'n Light Elektrikli Su Isıtıcı 1.7L",
        "base_cost": 320.00,
        "shipping_cost": 20.00,
        "stock": 80,
        "category": "Ev & Yaşam / Küçük Ev Aletleri",
        "initial_price": 599.00,
        "raw_specs": {
            "marka": "Tefal", "model": "KO850130", "kapasite": "1.7 litre",
            "güç": "2400W", "malzeme": "Cam", "garanti": "2 yıl",
        },
    },
    {
        "base_sku": "LOGITECH-MX3S",
        "title": "Logitech MX Master 3S Kablosuz Performans Mouse",
        "base_cost": 950.00,
        "shipping_cost": 20.00,
        "stock": 60,
        "category": "Bilgisayar / Çevre Birimleri",
        "initial_price": 1699.00,
        "raw_specs": {
            "marka": "Logitech", "model": "MX Master 3S", "bağlantı": "Bluetooth / USB-C",
            "dpi": "200-8000", "pil": "Şarj edilebilir", "uyumluluk": "Windows, macOS, Linux",
        },
    },
    {
        "base_sku": "SAMSUNG-A55",
        "title": "Samsung Galaxy A55 5G 256GB Akıllı Telefon",
        "base_cost": 8500.00,
        "shipping_cost": 45.00,
        "stock": 8,
        "category": "Elektronik / Cep Telefonu",
        "initial_price": 12999.00,
        "raw_specs": {
            "marka": "Samsung", "model": "Galaxy A55 5G", "depolama": "256GB",
            "ram": "8GB", "ekran": '6.6" Super AMOLED', "renk": "Sarı",
        },
    },
    {
        "base_sku": "DYSON-V15",
        "title": "Dyson V15 Detect Telsiz Elektrikli Süpürge",
        "base_cost": 12000.00,
        "shipping_cost": 0.00,
        "stock": 0,
        "category": "Ev & Yaşam / Elektrikli Süpürge",
        "initial_price": 18999.00,
        "raw_specs": {
            "marka": "Dyson", "model": "V15 Detect", "güç": "240 AW",
            "pil_ömrü": "60 dakika", "filtre": "HEPA", "renk": "Sarı/Nikel",
        },
    },
    {
        "base_sku": "LEGO-42151",
        "title": "LEGO Technic Bugatti Bolide 42151 Model Yapım Seti",
        "base_cost": 1200.00,
        "shipping_cost": 25.00,
        "stock": 25,
        "category": "Oyuncak / LEGO",
        "initial_price": 2199.00,
        "raw_specs": {
            "marka": "LEGO", "model": "Technic 42151", "parça_sayısı": "905",
            "yaş": "10+", "boyut": "14 x 8 x 4 cm", "renk": "Mavi/Kırmızı",
        },
    },
    {
        "base_sku": "NIKE-AIRMAX270",
        "title": "Nike Air Max 270 Erkek Spor Ayakkabı",
        "base_cost": 1800.00,
        "shipping_cost": 30.00,
        "stock": 3,
        "category": "Moda / Spor Ayakkabı",
        "initial_price": 3499.00,
        "raw_specs": {
            "marka": "Nike", "model": "Air Max 270", "taban": "Max Air",
            "ağırlık": "298g", "malzeme": "Mesh + Deri", "renk": "Siyah/Beyaz",
        },
    },
    {
        "base_sku": "NESCAFE-DOLCEGUSTO",
        "title": "Nescafé Dolce Gusto Genio S Plus Kahve Makinesi",
        "base_cost": 650.00,
        "shipping_cost": 30.00,
        "stock": 45,
        "category": "Ev & Yaşam / Kahve Makinesi",
        "initial_price": 1299.00,
        "raw_specs": {
            "marka": "Nescafé", "model": "Genio S Plus", "basınç": "15 bar",
            "kapasite": "0.8 litre", "ısıtma_süresi": "30 saniye", "renk": "Beyaz",
        },
    },
]

# ─── Mock log scenarios ─────────────────────────────────────────────────────────

_MOCK_SCENARIOS = [
    {
        "trigger_event": "competitor_price_change",
        "decision": "price_updated",
        "reasoning": "Rakip fiyatını düşürdü. Buybox'ı korumak için rakibin 0.50 TL altına indim. Kâr marjı hâlâ pozitif.",
        "confidence_score": 91.5,
        "has_buybox": True,
    },
    {
        "trigger_event": "competitor_price_change",
        "decision": "floor_hit",
        "reasoning": "Hedef fiyat floor fiyatının altına düşüyordu. Zarar etmemek için floor fiyatında bıraktım.",
        "confidence_score": 78.2,
        "has_buybox": False,
    },
    {
        "trigger_event": "scheduled",
        "decision": "price_updated",
        "reasoning": "Rakip fiyat medyanının altındaydım. Logistics balance stratejisi gereği medyana yaklaştım.",
        "confidence_score": 88.0,
        "has_buybox": True,
    },
    {
        "trigger_event": "scheduled",
        "decision": "no_action",
        "reasoning": "Mevcut fiyat rekabetçi konumda ve buybox bende. Fiyat değişikliğine gerek yok.",
        "confidence_score": 95.3,
        "has_buybox": True,
    },
    {
        "trigger_event": "low_stock",
        "decision": "price_updated",
        "reasoning": "Düşük stok tespit edildi. Kâr maksimizasyon stratejisine geçildi, fiyat artırıldı.",
        "confidence_score": 83.7,
        "has_buybox": False,
    },
    {
        "trigger_event": "competitor_price_change",
        "decision": "price_updated",
        "reasoning": "Buybox bizde ve rakip 2. sıradan 0.50 TL daha yükseğe çıktı. Parayı masada bırakmamak için fiyatı %5 kademeli artırdım.",
        "confidence_score": 89.1,
        "has_buybox": True,
    },
]


def _make_mock_logs(
    status: ProductPlatformStatus,
    log_count: int = 3,
) -> list[PricingAgentLog]:
    logs = []
    price = status.current_price or Decimal("100")
    floor = status.floor_price or Decimal("50")
    for i in range(log_count):
        scenario = _MOCK_SCENARIOS[(status.id + i) % len(_MOCK_SCENARIOS)]
        delta = Decimal(str(round(random.uniform(-30, 30), 2)))
        new_price = max(floor, price + delta) if scenario["decision"] == "price_updated" else price
        created_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=(log_count - i) * 8)
        logs.append(
            PricingAgentLog(
                product_platform_id=status.id,
                agent_name="PricingAgent",
                trigger_event=scenario["trigger_event"],
                input_snapshot={
                    "current_price": float(price),
                    "competitor_price": float(price - Decimal("0.50")),
                    "floor_price": float(floor),
                },
                reasoning=scenario["reasoning"],
                tool_calls={
                    "calls": [
                        "get_competitor_prices",
                        "calculate_floor_price",
                        "update_platform_price",
                        "log_decision",
                    ]
                },
                old_price=price,
                new_price=new_price,
                decision=scenario["decision"],
                duration_ms=random.randint(18000, 21000),
                confidence_score=scenario["confidence_score"],
                is_pending_approval=False,
                created_at=created_at,
            )
        )
        if scenario["decision"] == "price_updated":
            price = new_price
    return logs

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
        # Prefix SKU with user_id so multiple users can run the seed independently.
        # Product.sku has a global UNIQUE constraint — user-scoped prefix keeps it unique.
        sku = f"DEMO{user_id}-{p_data['base_sku']}"
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
            continue

        # Reload status rows to get their DB-assigned ids, then insert mock logs.
        fresh_statuses = (
            await session.execute(
                select(ProductPlatformStatus).where(
                    ProductPlatformStatus.product_id == product.id
                )
            )
        ).scalars().all()

        for status in fresh_statuses:
            mock_logs = _make_mock_logs(status, log_count=3)
            for log in mock_logs:
                session.add(log)

        # Set competitor_price only for marketplace platforms (own_site has no real competitors).
        # has_buybox is left to CompetitorWatcher — setting it here artificially
        # causes stale/wrong buybox display until the watcher first runs.
        for status in fresh_statuses:
            await session.refresh(status, attribute_names=["platform"])
            if status.platform.code != "own_site":
                status.competitor_price = (status.current_price or Decimal("0")) + Decimal(
                    str(round(random.uniform(10, 80), 2))
                )
                session.add(status)

        await session.commit()

    return DemoSeedResult(
        connections_created=connections_created,
        connections_skipped=connections_skipped,
        products_created=products_created,
        products_skipped=products_skipped,
        errors=errors,
    )


class ResetPricesResult(BaseModel):
    reset_count: int


@router.post("/reset-prices", response_model=ResetPricesResult)
async def reset_demo_prices(
    session: SessionDep,
    user_id: UserIdDep,
) -> ResetPricesResult:
    """Reset all product_platform_status prices to ceiling/2 (≈ original listing price).

    Use this after mock service restarts have caused cascading price degradation.
    """
    from sqlalchemy.orm import selectinload as _sl

    rows = (
        await session.execute(
            select(ProductPlatformStatus)
            .join(ProductPlatformStatus.product)
            .where(Product.user_id == user_id)
            .options(_sl(ProductPlatformStatus.product))
        )
    ).scalars().all()

    count = 0
    for pps in rows:
        if pps.ceiling_price:
            pps.current_price = (pps.ceiling_price / Decimal("2")).quantize(Decimal("0.01"))
            session.add(pps)
            count += 1

    await session.commit()
    return ResetPricesResult(reset_count=count)
