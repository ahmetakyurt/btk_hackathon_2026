"""Pricing API — manual trigger + log retrieval for PricingAgent."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.pricing_agent import (
    PricingAgent,
    PricingContext,
    PricingDecision,
    PricingStrategy,
)
from app.api.agents import broadcast_log
from app.api.products import _make_integration, compute_floor_price  # noqa: PLC2701
from app.config import get_settings
from app.core.deps import get_current_user_id
from app.db.models import PricingAgentLog, Platform, Product, ProductPlatformStatus
from app.db.session import get_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/pricing", tags=["pricing"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
UserIdDep = Annotated[int, Depends(get_current_user_id)]


# ─── Response schemas ─────────────────────────────────────────────────────────

class TriggerResponse(BaseModel):
    product_platform_id: int
    decision: str
    old_price: Decimal | None
    new_price: Decimal | None
    reasoning: str
    duration_ms: int
    log_id: int


class LogOut(BaseModel):
    id: int
    product_platform_id: int
    agent_name: str
    trigger_event: str
    sku: str | None
    platform_code: str | None
    old_price: Decimal | None
    new_price: Decimal | None
    decision: str
    reasoning: str | None
    tool_calls: Any
    duration_ms: int | None
    created_at: datetime


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/trigger/{product_platform_id}", response_model=TriggerResponse)
async def trigger_pricing(
    product_platform_id: int,
    session: SessionDep,
    user_id: UserIdDep,
    trigger_event: str = Query(default="manual"),
) -> TriggerResponse:
    """Manually run the PricingAgent for a product-platform status row."""
    pps = await session.scalar(
        select(ProductPlatformStatus)
        .where(ProductPlatformStatus.id == product_platform_id)
        .options(
            selectinload(ProductPlatformStatus.product),
            selectinload(ProductPlatformStatus.platform),
        )
    )
    if pps is None:
        raise HTTPException(status_code=404, detail="ProductPlatformStatus not found")
    if pps.product.user_id is not None and pps.product.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not your product")
    if pps.status != "listed":
        raise HTTPException(
            status_code=400,
            detail=f"Product is not listed on this platform (status={pps.status})",
        )
    if pps.external_id is None:
        raise HTTPException(status_code=400, detail="No external_id — not listed yet")

    product: Product = pps.product
    platform: Platform = pps.platform

    current_price = pps.current_price or Decimal("0")
    floor_price = pps.floor_price or compute_floor_price(
        product.base_cost,
        product.shipping_cost,
        Decimal(str(platform.commission_rate)),
    )
    ceiling_price = pps.ceiling_price or (floor_price * Decimal("2")).quantize(Decimal("0.01"))

    ctx = PricingContext(
        product_platform_id=pps.id,
        sku=product.sku,
        platform_code=platform.code,
        strategy=PricingStrategy(platform.pricing_strategy),
        current_price=current_price,
        floor_price=floor_price,
        ceiling_price=ceiling_price,
        base_cost=product.base_cost,
        shipping_cost=product.shipping_cost,
        commission_rate=Decimal(str(platform.commission_rate)),
        external_id=pps.external_id,
    )

    settings = get_settings()
    agent = PricingAgent(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
        timeout=float(settings.gemini_timeout_seconds),
    )
    integration = _make_integration(platform)

    result = await agent.run(ctx, integration, trigger_event=trigger_event)

    log = PricingAgentLog(
        product_platform_id=pps.id,
        agent_name="PricingAgent",
        trigger_event=trigger_event,
        input_snapshot={
            "sku": product.sku,
            "platform_code": platform.code,
            "strategy": platform.pricing_strategy,
            "current_price": float(current_price),
            "floor_price": float(floor_price),
            "competitor_price": float(pps.competitor_price) if pps.competitor_price else None,
        },
        reasoning=result.reasoning,
        tool_calls=result.tool_calls,
        old_price=result.old_price,
        new_price=result.new_price,
        decision=result.decision.value,
        duration_ms=result.duration_ms,
    )
    session.add(log)

    if result.decision in (PricingDecision.PRICE_UPDATED, PricingDecision.FLOOR_HIT):
        pps.current_price = result.new_price
        pps.last_synced_at = datetime.now(UTC)

    await session.commit()
    await session.refresh(log)

    # Broadcast to SSE subscribers (manual trigger also shows in live-log panel)
    broadcast_user_id = pps.product.user_id or user_id
    await broadcast_log({
        "id": log.id,
        "product_platform_id": log.product_platform_id,
        "agent_name": log.agent_name,
        "trigger_event": log.trigger_event,
        "sku": product.sku,
        "platform_code": platform.code,
        "old_price": float(log.old_price) if log.old_price else None,
        "new_price": float(log.new_price) if log.new_price else None,
        "decision": log.decision,
        "reasoning": log.reasoning,
        "tool_calls": log.tool_calls,
        "duration_ms": log.duration_ms,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }, user_id=broadcast_user_id)

    return TriggerResponse(
        product_platform_id=pps.id,
        decision=result.decision.value,
        old_price=result.old_price,
        new_price=result.new_price,
        reasoning=result.reasoning,
        duration_ms=result.duration_ms,
        log_id=log.id,
    )


def _log_to_out(r: PricingAgentLog) -> LogOut:
    pps = r.product_platform
    return LogOut(
        id=r.id,
        product_platform_id=r.product_platform_id,
        agent_name=r.agent_name,
        trigger_event=r.trigger_event,
        sku=pps.product.sku if pps and pps.product else None,
        platform_code=pps.platform.code if pps and pps.platform else None,
        old_price=r.old_price,
        new_price=r.new_price,
        decision=r.decision,
        reasoning=r.reasoning,
        tool_calls=r.tool_calls,
        duration_ms=r.duration_ms,
        created_at=r.created_at,
    )


_LOG_LOAD_OPTIONS = [
    selectinload(PricingAgentLog.product_platform).selectinload(ProductPlatformStatus.product),
    selectinload(PricingAgentLog.product_platform).selectinload(ProductPlatformStatus.platform),
]


@router.get("/logs", response_model=list[LogOut])
async def list_pricing_logs(
    session: SessionDep,
    user_id: UserIdDep,
    limit: int = Query(default=50, le=200),
) -> list[LogOut]:
    """Most recent pricing decisions for the current user — used by live logs dashboard."""
    rows = await session.scalars(
        select(PricingAgentLog)
        .join(PricingAgentLog.product_platform)
        .join(ProductPlatformStatus.product)
        .where(Product.user_id == user_id)
        .order_by(PricingAgentLog.created_at.desc())
        .limit(limit)
        .options(*_LOG_LOAD_OPTIONS)
    )
    return [_log_to_out(r) for r in rows.all()]


@router.get("/logs/{product_platform_id}", response_model=list[LogOut])
async def get_platform_pricing_logs(
    product_platform_id: int,
    session: SessionDep,
    user_id: UserIdDep,
    limit: int = Query(default=20, le=100),
) -> list[LogOut]:
    # Verify ownership first
    pps = await session.scalar(
        select(ProductPlatformStatus)
        .where(ProductPlatformStatus.id == product_platform_id)
        .options(selectinload(ProductPlatformStatus.product))
    )
    if pps is None:
        raise HTTPException(status_code=404, detail="ProductPlatformStatus not found")
    if pps.product.user_id is not None and pps.product.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not your product")

    rows = await session.scalars(
        select(PricingAgentLog)
        .where(PricingAgentLog.product_platform_id == product_platform_id)
        .order_by(PricingAgentLog.created_at.desc())
        .limit(limit)
        .options(*_LOG_LOAD_OPTIONS)
    )
    return [_log_to_out(r) for r in rows.all()]
