"""CompetitorWatcher: async polling loop that detects competitor price changes
and triggers PricingAgent automatically.

Started as an asyncio.Task in FastAPI lifespan. One poll = one DB query to load
all active listed product-platform statuses; each listing is checked independently
so one platform being down doesn't block the others.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.agents.pricing_agent import PricingAgent, PricingContext, PricingDecision, PricingStrategy
from app.api.products import _make_integration, compute_floor_price  # noqa: PLC2701
from app.config import get_settings
from app.db.models import PricingAgentLog, Platform, Product, ProductPlatformStatus
from app.db.session import SessionLocal
from app.integrations.base import IntegrationError

logger = logging.getLogger(__name__)

_MIN_COMPETITOR_DELTA = Decimal("0.50")  # TL — ignore smaller price changes


class CompetitorWatcher:
    """Polls all active listings, reacts to competitor price drops via PricingAgent."""

    def __init__(
        self,
        poll_interval: int = 5,
        on_log: Callable[..., Awaitable[None]] | None = None,
    ) -> None:
        self._poll_interval = poll_interval
        self._on_log = on_log  # SSE broadcast hook — injected at startup
        self._running = False

    async def start(self) -> None:
        self._running = True
        logger.info("CompetitorWatcher started (poll_interval=%ds)", self._poll_interval)
        while self._running:
            try:
                await self._poll_once()
            except Exception as exc:
                logger.error("CompetitorWatcher unexpected error: %s", exc, exc_info=True)
            await asyncio.sleep(self._poll_interval)

    def stop(self) -> None:
        self._running = False

    # ─── Internal ─────────────────────────────────────────────────────────

    async def _poll_once(self) -> None:
        """Load all listable PPS IDs in one query; process each independently."""
        async with SessionLocal() as session:
            rows = (await session.scalars(
                select(ProductPlatformStatus)
                .where(
                    ProductPlatformStatus.status == "listed",
                    ProductPlatformStatus.external_id.isnot(None),
                )
                .options(
                    selectinload(ProductPlatformStatus.platform),
                )
            )).all()
            pps_ids = [
                pps.id for pps in rows
                if pps.platform.is_active
            ]

        for pps_id in pps_ids:
            try:
                await self._check_one(pps_id)
            except Exception as exc:
                logger.error("Watcher error for PPS id=%s: %s", pps_id, exc)

    async def _check_one(self, pps_id: int) -> None:
        """Check a single ProductPlatformStatus in its own session."""
        async with SessionLocal() as session:
            pps = await session.scalar(
                select(ProductPlatformStatus)
                .where(ProductPlatformStatus.id == pps_id)
                .options(
                    selectinload(ProductPlatformStatus.product),
                    selectinload(ProductPlatformStatus.platform),
                )
            )
            if pps is None:
                return

            product: Product = pps.product
            platform: Platform = pps.platform
            integration = _make_integration(platform)

            # Fetch current competitor snapshot
            try:
                snapshot = await integration.get_competitor_snapshot(pps.external_id)
            except IntegrationError as exc:
                logger.debug("Competitor fetch failed for %s/%s: %s", platform.code, product.sku, exc)
                return

            if not snapshot.competitors:
                # own_site has no competitors — nothing to react to
                return

            new_min = min(c.price for c in snapshot.competitors)
            old_min = pps.competitor_price
            own_has_buybox = snapshot.own_has_buybox

            # Always update competitor_price + has_buybox in DB
            pps.competitor_price = new_min
            pps.has_buybox = own_has_buybox
            # Naive UTC — DB column is TIMESTAMP WITHOUT TIME ZONE
            pps.last_synced_at = datetime.now(UTC).replace(tzinfo=None)

            # Only trigger PricingAgent if min competitor price changed meaningfully
            if not _price_changed(old_min, new_min):
                await session.commit()
                return

            logger.info(
                "Competitor price change detected: %s/%s %s → %s TL",
                platform.code, product.sku,
                old_min or "?", new_min,
            )

            # Build pricing context
            floor_price = pps.floor_price or compute_floor_price(
                product.base_cost,
                product.shipping_cost,
                Decimal(str(platform.commission_rate)),
            )
            ceiling_price = pps.ceiling_price or (floor_price * Decimal("2")).quantize(Decimal("0.01"))
            current_price = pps.current_price or floor_price

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

            result = await agent.run(ctx, integration, trigger_event="competitor_change")

            # Persist log
            log = PricingAgentLog(
                product_platform_id=pps.id,
                agent_name="PricingAgent",
                trigger_event="competitor_change",
                input_snapshot={
                    "sku": product.sku,
                    "platform_code": platform.code,
                    "strategy": platform.pricing_strategy,
                    "current_price": float(current_price),
                    "floor_price": float(floor_price),
                    "competitor_price": float(new_min),
                    "old_competitor_price": float(old_min) if old_min else None,
                },
                reasoning=result.reasoning,
                tool_calls=result.tool_calls,
                old_price=result.old_price,
                new_price=result.new_price,
                decision=result.decision.value,
                duration_ms=result.duration_ms,
                confidence_score=result.confidence_score,
                is_pending_approval=result.requires_approval,
            )
            session.add(log)

            if result.decision in (PricingDecision.PRICE_UPDATED, PricingDecision.FLOOR_HIT):
                pps.current_price = result.new_price

            pps.last_confidence_score = result.confidence_score
            if result.requires_approval:
                pps.requires_approval = True

            await session.commit()
            await session.refresh(log)

            # Broadcast to SSE subscribers (scoped to the product owner)
            if self._on_log is not None and product.user_id is not None:
                log_data = {
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
                    "created_at": (log.created_at.isoformat() + "Z") if log.created_at else None,
                }
                await self._on_log(log_data, user_id=product.user_id)


# ─── Helper ───────────────────────────────────────────────────────────────────

def _price_changed(old: Decimal | None, new: Decimal) -> bool:
    """True if the competitor price moved by at least the threshold."""
    return old is None or abs(new - old) >= _MIN_COMPETITOR_DELTA
