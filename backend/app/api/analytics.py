"""Analytics API — dashboard aggregations for platform-level KPIs."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.pricing import LogOut, _log_to_out
from app.core.deps import get_current_user_id
from app.db.models import PricingAgentLog, Platform, Product, ProductPlatformStatus
from app.db.session import get_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analytics", tags=["analytics"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
UserIdDep = Annotated[int, Depends(get_current_user_id)]


class PlatformAnalytics(BaseModel):
    platform_code: str
    platform_name: str
    total_profit: float
    avg_price: float
    buybox_win_rate: float
    total_decisions: int
    floor_hit_count: int
    last_decision_at: datetime | None


class DashboardSummary(BaseModel):
    platforms: list[PlatformAnalytics]
    recent_decisions: list[LogOut]
    total_products: int
    total_listed: int


_LOG_LOAD_OPTIONS = [
    selectinload(PricingAgentLog.product_platform).selectinload(ProductPlatformStatus.product),
    selectinload(PricingAgentLog.product_platform).selectinload(ProductPlatformStatus.platform),
]


@router.get("/dashboard", response_model=DashboardSummary)
async def get_dashboard(
    session: SessionDep,
    user_id: UserIdDep,
) -> DashboardSummary:
    # Decide + floor counts per platform from pricing_agent_logs
    decisions_rows = await session.execute(
        select(
            Platform.code,
            Platform.display_name,
            func.count(PricingAgentLog.id).label("total_decisions"),
            func.sum(case((PricingAgentLog.decision == "floor_hit", 1), else_=0)).label("floor_hit_count"),
            func.max(PricingAgentLog.created_at).label("last_decision_at"),
        )
        .select_from(PricingAgentLog)
        .join(PricingAgentLog.product_platform)
        .join(ProductPlatformStatus.platform)
        .join(ProductPlatformStatus.product)
        .where(Product.user_id == user_id)
        .group_by(Platform.code, Platform.display_name)
    )

    # Avg listed price per platform
    avg_rows = await session.execute(
        select(
            Platform.code,
            func.avg(ProductPlatformStatus.current_price).label("avg_price"),
        )
        .select_from(ProductPlatformStatus)
        .join(ProductPlatformStatus.platform)
        .join(ProductPlatformStatus.product)
        .where(Product.user_id == user_id, ProductPlatformStatus.status == "listed")
        .group_by(Platform.code)
    )
    avg_map: dict[str, float] = {}
    for r in avg_rows:
        avg_map[r.code] = float(r.avg_price) if r.avg_price else 0.0

    # Profit from price_updated decisions
    profit_rows = await session.execute(
        select(
            Platform.code,
            func.sum(PricingAgentLog.new_price - Product.base_cost - Product.shipping_cost).label("profit"),
        )
        .select_from(PricingAgentLog)
        .join(PricingAgentLog.product_platform)
        .join(ProductPlatformStatus.platform)
        .join(ProductPlatformStatus.product)
        .where(
            Product.user_id == user_id,
            PricingAgentLog.decision == "price_updated",
        )
        .group_by(Platform.code)
    )
    profit_map: dict[str, float] = {}
    for r in profit_rows:
        profit_map[r.code] = float(r.profit) if r.profit else 0.0

    # Buybox win rate from product_platform_status
    buybox_rows = await session.execute(
        select(
            Platform.code,
            func.count(ProductPlatformStatus.id).label("total"),
            func.sum(case((ProductPlatformStatus.has_buybox.is_(True), 1), else_=0)).label("wins"),
        )
        .select_from(ProductPlatformStatus)
        .join(ProductPlatformStatus.platform)
        .join(ProductPlatformStatus.product)
        .where(Product.user_id == user_id, ProductPlatformStatus.status == "listed")
        .group_by(Platform.code)
    )
    buybox_map: dict[str, float] = {}
    for r in buybox_rows:
        total = r.total or 0
        wins = r.wins or 0
        buybox_map[r.code] = wins / total if total > 0 else 0.0

    platforms: list[PlatformAnalytics] = []
    for row in decisions_rows:
        code = row.code
        platforms.append(
            PlatformAnalytics(
                platform_code=code,
                platform_name=row.display_name,
                total_profit=profit_map.get(code, 0.0),
                avg_price=avg_map.get(code, 0.0),
                buybox_win_rate=buybox_map.get(code, 0.0),
                total_decisions=row.total_decisions or 0,
                floor_hit_count=row.floor_hit_count or 0,
                last_decision_at=row.last_decision_at,
            )
        )

    # Recent decisions (last 10)
    recent_rows = await session.scalars(
        select(PricingAgentLog)
        .join(PricingAgentLog.product_platform)
        .join(ProductPlatformStatus.product)
        .where(Product.user_id == user_id)
        .order_by(PricingAgentLog.created_at.desc())
        .limit(10)
        .options(*_LOG_LOAD_OPTIONS)
    )
    recent_decisions = [_log_to_out(r) for r in recent_rows.all()]

    total_products = (
        await session.scalar(select(func.count(Product.id)).where(Product.user_id == user_id))
    ) or 0

    total_listed = (
        await session.scalar(
            select(func.count(ProductPlatformStatus.id))
            .join(ProductPlatformStatus.product)
            .where(Product.user_id == user_id, ProductPlatformStatus.status == "listed")
        )
    ) or 0

    return DashboardSummary(
        platforms=platforms,
        recent_decisions=recent_decisions,
        total_products=total_products,
        total_listed=total_listed,
    )
