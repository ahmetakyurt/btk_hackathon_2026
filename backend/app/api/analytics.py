"""Analytics API — dashboard aggregations for platform-level KPIs."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.pricing import LogOut, _log_to_out
from app.config import get_settings
from app.core.deps import get_current_user_id
from app.db.models import PricingAgentLog, Platform, Product, ProductPlatformStatus
from app.db.session import get_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analytics", tags=["analytics"])

LOW_STOCK_THRESHOLD = 10

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


class Insight(BaseModel):
    title: str
    description: str
    priority: int  # 1=highest, 5=lowest
    platform_code: str | None = None
    action_type: str  # "pricing", "stock", "listing", "general"


class InsightsResponse(BaseModel):
    insights: list[Insight]
    generated_at: datetime
    is_ai_generated: bool


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


# ─── Insights ─────────────────────────────────────────────────────────────────

@router.get("/insights", response_model=InsightsResponse)
async def get_insights(
    session: SessionDep,
    user_id: UserIdDep,
) -> InsightsResponse:
    """AI-powered (Gemini) action recommendations; falls back to rule-based."""
    since = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=24)

    # Platform analytics for context
    platform_rows = (await session.execute(
        select(
            Platform.code,
            Platform.display_name,
            Platform.pricing_strategy,
            func.count(PricingAgentLog.id).label("total_decisions"),
            func.sum(case((PricingAgentLog.decision == "floor_hit", 1), else_=0)).label("floor_hits"),
            func.sum(case((PricingAgentLog.decision == "price_updated", 1), else_=0)).label("price_updates"),
        )
        .select_from(PricingAgentLog)
        .join(PricingAgentLog.product_platform)
        .join(ProductPlatformStatus.platform)
        .join(ProductPlatformStatus.product)
        .where(Product.user_id == user_id, PricingAgentLog.created_at >= since)
        .group_by(Platform.code, Platform.display_name, Platform.pricing_strategy)
    )).all()

    # Buybox stats
    buybox_rows = (await session.execute(
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
    )).all()
    buybox_map = {r.code: (r.wins or 0) / r.total for r in buybox_rows if r.total}

    # Low-stock products
    low_stock_count = (await session.scalar(
        select(func.count(Product.id)).where(
            Product.user_id == user_id,
            Product.stock <= LOW_STOCK_THRESHOLD,
            Product.stock > 0,
        )
    )) or 0

    # Pending approvals
    pending_count = (await session.scalar(
        select(func.count(ProductPlatformStatus.id))
        .join(ProductPlatformStatus.product)
        .where(Product.user_id == user_id, ProductPlatformStatus.requires_approval.is_(True))
    )) or 0

    context_str = _build_insights_context(platform_rows, buybox_map, low_stock_count, pending_count)

    settings = get_settings()
    from app.core.gemini_client import gemini_available
    ai_insights: list[Insight] = []
    if gemini_available():
        try:
            ai_insights = await asyncio.wait_for(
                _generate_ai_insights(settings.gemini_model, context_str),
                timeout=float(settings.gemini_timeout_seconds),
            )
        except Exception as exc:
            logger.warning("Insights Gemini failed — using rule-based fallback: %s", exc)

    insights = ai_insights if ai_insights else _rule_based_insights(
        platform_rows, buybox_map, low_stock_count, pending_count
    )

    return InsightsResponse(
        insights=insights,
        generated_at=datetime.now(UTC),
        is_ai_generated=bool(ai_insights),
    )


def _build_insights_context(platform_rows: list, buybox_map: dict, low_stock: int, pending: int) -> str:
    lines = [f"Son 24 saatte platform performansı:"]
    for r in platform_rows:
        buybox_pct = int((buybox_map.get(r.code, 0)) * 100)
        lines.append(
            f"- {r.display_name} ({r.code}): strateji={r.pricing_strategy}, "
            f"toplam_karar={r.total_decisions}, fiyat_güncelleme={r.price_updates}, "
            f"taban_fiyat_isabeti={r.floor_hits}, buybox_oranı=%{buybox_pct}"
        )
    if not platform_rows:
        lines.append("- Henüz hiç fiyatlandırma kararı yok.")
    lines.append(f"Düşük stoklu ürün sayısı (≤{LOW_STOCK_THRESHOLD} adet): {low_stock}")
    lines.append(f"İnsan onayı bekleyen karar sayısı: {pending}")
    return "\n".join(lines)


async def _generate_ai_insights(model: str, context: str) -> list[Insight]:
    from app.core.gemini_client import build_genai_client

    client = build_genai_client()
    if client is None:
        return []
    prompt = f"""Sen OptiPrice AI'ın analiz asistanısın. Bir e-ticaret satıcısına Türkçe öneriler sun.

VERİ:
{context}

Yukarıdaki verilere göre satıcıya 3-5 somut, uygulanabilir Türkçe öneri üret.
Sadece aşağıdaki JSON formatında yanıt ver, başka hiçbir şey yazma:

[
  {{
    "title": "Kısa başlık (maks 60 karakter)",
    "description": "Açıklama ve ne yapılması gerektiği (maks 200 karakter)",
    "priority": 1,
    "platform_code": "trendyol veya amazon veya own_site veya null",
    "action_type": "pricing veya stock veya listing veya general"
  }}
]

priority: 1=acil, 2=önemli, 3=normal, 4=düşük, 5=bilgi"""

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=model,
        contents=prompt,
    )

    text = response.text.strip()
    # Strip markdown code block if present
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    raw = json.loads(text)
    return [
        Insight(
            title=item["title"],
            description=item["description"],
            priority=int(item.get("priority", 3)),
            platform_code=item.get("platform_code") or None,
            action_type=item.get("action_type", "general"),
        )
        for item in raw
        if isinstance(item, dict)
    ]


def _rule_based_insights(
    platform_rows: list, buybox_map: dict, low_stock: int, pending: int
) -> list[Insight]:
    insights: list[Insight] = []

    if pending > 0:
        insights.append(Insight(
            title=f"{pending} karar onay bekliyor",
            description=f"Güven skoru düşük olduğu için {pending} fiyat kararı askıya alındı. İnceleyip onaylayın veya reddedin.",
            priority=1,
            platform_code=None,
            action_type="pricing",
        ))

    if low_stock > 0:
        insights.append(Insight(
            title=f"{low_stock} ürün kritik stok seviyesinde",
            description=f"Stok ≤{LOW_STOCK_THRESHOLD} olan ürünler var. Ajan otomatik olarak kâr_maks stratejisine geçecek.",
            priority=2,
            platform_code=None,
            action_type="stock",
        ))

    for r in platform_rows:
        buybox_rate = buybox_map.get(r.code, 0)
        if buybox_rate < 0.3 and r.total_decisions > 0:
            insights.append(Insight(
                title=f"{r.display_name} buybox kaybediliyor",
                description=f"Buybox kazanma oranı %{int(buybox_rate * 100)}. Rakip fiyatlarını kontrol edin.",
                priority=2,
                platform_code=r.code,
                action_type="pricing",
            ))
        if r.floor_hits and r.floor_hits > 2:
            insights.append(Insight(
                title=f"{r.display_name} taban fiyat baskısı",
                description=f"Son 24 saatte {r.floor_hits} kez taban fiyata ulaşıldı. Maliyet yapısını gözden geçirin.",
                priority=3,
                platform_code=r.code,
                action_type="pricing",
            ))

    if not platform_rows:
        insights.append(Insight(
            title="Henüz fiyatlandırma kararı yok",
            description="Ürün ekleyin ve platform bağlantılarını kurun; ajan otomatik fiyat kararları almaya başlar.",
            priority=3,
            platform_code=None,
            action_type="general",
        ))

    return insights[:5]
