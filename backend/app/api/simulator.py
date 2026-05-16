"""Simulator API — competitor price manipulation proxy for jury demo."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.core.deps import get_current_user_id
from app.db.models import Platform, Product, ProductPlatformStatus
from app.db.session import get_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/simulator", tags=["simulator"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
UserIdDep = Annotated[int, Depends(get_current_user_id)]


def _platform_base_url(platform_code: str) -> str | None:
    settings = get_settings()
    return {
        "trendyol": settings.mock_trendyol_url,
        "amazon": settings.mock_amazon_url,
    }.get(platform_code)


async def _ensure_product_in_mock(
    pps: ProductPlatformStatus,
    base_url: str,
    client: httpx.AsyncClient,
) -> str | None:
    """Re-create a product in a mock service. Returns the new external_id or None.

    Uses ceiling_price/2 (≈ original listing price) instead of current_price to prevent
    cascading price degradation: after each mock restart the price would otherwise be
    re-seeded at whatever degraded value the agent last wrote, creating a downward spiral.
    """
    product = pps.product
    # ceiling_price = initial_price × 2, so ceiling/2 ≈ original listing price.
    relist_price = (
        float(pps.ceiling_price) / 2.0
        if pps.ceiling_price
        else float(pps.current_price) if pps.current_price
        else 100.0
    )
    payload: dict[str, Any] = {
        "sku": product.sku,
        "title": pps.ai_generated_title or product.title,
        "description": pps.ai_generated_desc or "",
        "category": product.category or "",
        "price": relist_price,
        "stock": product.stock,
        "keywords": [],
        "raw_specs": {str(k): str(v) for k, v in (product.raw_specs or {}).items()},
    }
    if "amazon" in base_url:
        payload["fulfillment"] = "FBM"

    try:
        r = await client.post(f"{base_url}/products", json=payload)
        r.raise_for_status()
        data = r.json()
        new_external_id = data["external_id"]
        logger.info("Re-created product %s in mock service (%s) → %s", product.sku, base_url, new_external_id)
        return new_external_id
    except Exception as exc:
        logger.warning("Failed to re-create product %s in mock service %s: %s", product.sku, base_url, exc)
        return None


# ─── Response schemas ─────────────────────────────────────────────────────────

class CompetitorInfo(BaseModel):
    seller_name: str
    price: float
    has_buybox: bool


class PlatformSimState(BaseModel):
    product_platform_id: int
    sku: str
    product_title: str
    platform_code: str
    platform_name: str
    external_id: str
    own_price: float
    own_has_buybox: bool
    competitors: list[CompetitorInfo]


class SetCompetitorPriceRequest(BaseModel):
    product_platform_id: int
    seller_name: str
    price: Decimal


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/state", response_model=list[PlatformSimState])
async def get_simulator_state(session: SessionDep, user_id: UserIdDep) -> list[PlatformSimState]:
    """Return current competitor state for the user's listed products on competitive platforms."""
    rows = await session.scalars(
        select(ProductPlatformStatus)
        .join(ProductPlatformStatus.product)
        .where(Product.user_id == user_id)
        .where(ProductPlatformStatus.status == "listed")
        .where(ProductPlatformStatus.external_id.isnot(None))
        .options(
            selectinload(ProductPlatformStatus.product),
            selectinload(ProductPlatformStatus.platform),
        )
    )

    results: list[PlatformSimState] = []
    async with httpx.AsyncClient(timeout=5.0) as client:
        for pps in rows.all():
            platform_code = pps.platform.code
            base_url = _platform_base_url(platform_code)
            if base_url is None:
                continue  # own_site has no competitor simulation

            # Default fallback values from Supabase
            own_price = float(pps.current_price) if pps.current_price else 0.0
            own_has_buybox = pps.has_buybox or False
            competitors: list[CompetitorInfo] = []

            try:
                r = await client.get(f"{base_url}/products/{pps.external_id}/competitors")
                if r.status_code == 404:
                    # Product missing from mock service — try to re-create it
                    new_external_id = await _ensure_product_in_mock(pps, base_url, client)
                    if new_external_id:
                        pps.external_id = new_external_id
                        # Fetch competitors first to get the actual price the mock assigned
                        r2 = await client.get(f"{base_url}/products/{new_external_id}/competitors")
                        r2.raise_for_status()
                        data2 = r2.json()
                        own_price = float(data2["own_price"])
                        own_has_buybox = data2["own_has_buybox"]
                        competitors = [CompetitorInfo(**c) for c in data2["competitors"]]
                        # Sync current_price in DB to match the freshly listed price,
                        # so the next agent run starts from the correct baseline.
                        from decimal import Decimal as _D
                        pps.current_price = _D(str(own_price))
                        session.add(pps)
                        await session.commit()
                    # If re-creation failed, fall through to add with fallback values
                else:
                    r.raise_for_status()
                    data = r.json()
                    own_price = float(data["own_price"])
                    own_has_buybox = data["own_has_buybox"]
                    competitors = [CompetitorInfo(**c) for c in data["competitors"]]
                    # Sync live buybox status back to DB so product detail page stays accurate.
                    if pps.has_buybox != own_has_buybox:
                        pps.has_buybox = own_has_buybox
                        session.add(pps)
                        await session.commit()
            except Exception as exc:
                logger.warning(
                    "Could not fetch competitors for %s/%s (will show fallback): %s",
                    platform_code, pps.external_id, exc,
                )

            results.append(
                PlatformSimState(
                    product_platform_id=pps.id,
                    sku=pps.product.sku,
                    product_title=pps.product.title,
                    platform_code=platform_code,
                    platform_name=pps.platform.display_name,
                    external_id=pps.external_id,
                    own_price=own_price,
                    own_has_buybox=own_has_buybox,
                    competitors=competitors,
                )
            )

    return results


@router.post("/set-competitor-price")
async def set_competitor_price(
    body: SetCompetitorPriceRequest,
    session: SessionDep,
    user_id: UserIdDep,
) -> dict[str, Any]:
    """Proxy a competitor price change to the appropriate mock service."""
    pps = await session.scalar(
        select(ProductPlatformStatus)
        .where(ProductPlatformStatus.id == body.product_platform_id)
        .options(
            selectinload(ProductPlatformStatus.platform),
            selectinload(ProductPlatformStatus.product),
        )
    )
    if pps is None:
        raise HTTPException(status_code=404, detail="ProductPlatformStatus not found")
    if pps.product.user_id is not None and pps.product.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not your product")

    platform_code = pps.platform.code
    base_url = _platform_base_url(platform_code)
    if base_url is None:
        raise HTTPException(
            status_code=400,
            detail=f"Platform '{platform_code}' has no competitor simulation",
        )

    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            r = await client.post(
                f"{base_url}/admin/competitor-price",
                json={
                    "external_id": pps.external_id,
                    "seller_name": body.seller_name,
                    "price": float(body.price),
                },
            )
            if r.status_code == 404:
                # Product or competitor missing from mock — re-create product with fresh competitors
                new_id = await _ensure_product_in_mock(pps, base_url, client)
                if new_id is None:
                    raise HTTPException(status_code=503, detail="Mock servis geçici olarak kullanılamıyor. Lütfen tekrar deneyin.")
                pps.external_id = new_id
                session.add(pps)
                await session.commit()
                # Fetch new competitors and pick the first one as target
                r2 = await client.get(f"{base_url}/products/{new_id}/competitors")
                r2.raise_for_status()
                competitors_data = r2.json()
                competitors_list = competitors_data.get("competitors", [])
                if not competitors_list:
                    raise HTTPException(status_code=400, detail="Bu platformda rakip bulunamadı.")
                target = competitors_list[0]
                # Set price on the first competitor
                r3 = await client.post(
                    f"{base_url}/admin/competitor-price",
                    json={
                        "external_id": new_id,
                        "seller_name": target["seller_name"],
                        "price": float(body.price),
                    },
                )
                r3.raise_for_status()
                return {
                    **r3.json(),
                    "note": f"Ürün mock serviste yeniden oluşturuldu. Rakip '{target['seller_name']}' fiyatı güncellendi.",
                    "seller_name": target["seller_name"],
                }
            r.raise_for_status()
            # Sync buybox + competitor_price to DB so product page reflects new state immediately.
            try:
                snap = await client.get(f"{base_url}/products/{pps.external_id}/competitors")
                if snap.status_code == 200:
                    snap_data = snap.json()
                    new_has_buybox = bool(snap_data.get("own_has_buybox", False))
                    comps = snap_data.get("competitors", [])
                    if comps:
                        from decimal import Decimal as _D
                        new_min = min(_D(str(c["price"])) for c in comps)
                        pps.competitor_price = new_min
                    pps.has_buybox = new_has_buybox
                    session.add(pps)
                    await session.commit()
            except Exception:
                pass  # best-effort sync; CompetitorWatcher will catch up within 5s
            return r.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=str(exc))
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"Mock service unavailable: {exc}")
