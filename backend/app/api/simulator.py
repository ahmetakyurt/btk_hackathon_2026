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
from app.db.models import Platform, ProductPlatformStatus
from app.db.session import get_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/simulator", tags=["simulator"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _platform_base_url(platform_code: str) -> str | None:
    settings = get_settings()
    return {
        "trendyol": settings.mock_trendyol_url,
        "amazon": settings.mock_amazon_url,
    }.get(platform_code)


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
async def get_simulator_state(session: SessionDep) -> list[PlatformSimState]:
    """Return current competitor state for all listed products on competitive platforms."""
    rows = await session.scalars(
        select(ProductPlatformStatus)
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
                continue  # own_site has no competitors
            try:
                r = await client.get(f"{base_url}/products/{pps.external_id}/competitors")
                r.raise_for_status()
                data = r.json()
                results.append(
                    PlatformSimState(
                        product_platform_id=pps.id,
                        sku=pps.product.sku,
                        product_title=pps.product.title,
                        platform_code=platform_code,
                        platform_name=pps.platform.display_name,
                        external_id=pps.external_id,
                        own_price=float(data["own_price"]),
                        own_has_buybox=data["own_has_buybox"],
                        competitors=[CompetitorInfo(**c) for c in data["competitors"]],
                    )
                )
            except Exception as exc:
                logger.warning(
                    "Could not fetch competitors for %s/%s: %s",
                    platform_code, pps.external_id, exc,
                )

    return results


@router.post("/set-competitor-price")
async def set_competitor_price(
    body: SetCompetitorPriceRequest,
    session: SessionDep,
) -> dict[str, Any]:
    """Proxy a competitor price change to the appropriate mock service."""
    pps = await session.scalar(
        select(ProductPlatformStatus)
        .where(ProductPlatformStatus.id == body.product_platform_id)
        .options(selectinload(ProductPlatformStatus.platform))
    )
    if pps is None:
        raise HTTPException(status_code=404, detail="ProductPlatformStatus not found")

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
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"Mock service unavailable: {exc}")
