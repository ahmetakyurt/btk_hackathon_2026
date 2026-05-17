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
from datetime import UTC, datetime, timedelta
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
_LOW_STOCK_THRESHOLD = 10                # units — trigger profit_max below this
_LOW_STOCK_COOLDOWN_HOURS = 1            # hours — re-trigger low_stock at most once/hour


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

            # ── own_site: no marketplace competitors; use sibling platform prices ──
            if not snapshot.competitors:
                if platform.code != "own_site":
                    return  # non-own_site with no competitors — nothing to do
                await self._check_own_site(pps, product, platform, session)
                return

            new_min = min(c.price for c in snapshot.competitors)
            old_min = pps.competitor_price
            own_has_buybox = snapshot.own_has_buybox

            # Always update competitor_price + has_buybox in DB
            pps.competitor_price = new_min
            pps.has_buybox = own_has_buybox
            # Naive UTC — DB column is TIMESTAMP WITHOUT TIME ZONE
            pps.last_synced_at = datetime.now(UTC).replace(tzinfo=None)

            stock_is_low = product.stock <= _LOW_STOCK_THRESHOLD
            price_did_change = _price_changed(old_min, new_min)

            # Determine whether to fire the agent
            should_fire = price_did_change
            if stock_is_low and not price_did_change:
                # Fire at most once per cooldown window to avoid spam
                cooldown_start = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=_LOW_STOCK_COOLDOWN_HOURS)
                recent_low_stock = await session.scalar(
                    select(PricingAgentLog).where(
                        PricingAgentLog.product_platform_id == pps.id,
                        PricingAgentLog.trigger_event == "low_stock",
                        PricingAgentLog.created_at >= cooldown_start,
                    ).limit(1)
                )
                if recent_low_stock is None:
                    should_fire = True

            if not should_fire:
                await session.commit()
                return

            if price_did_change:
                logger.info(
                    "Competitor price change detected: %s/%s %s → %s TL",
                    platform.code, product.sku, old_min or "?", new_min,
                )
            if stock_is_low:
                logger.info(
                    "Low stock trigger: %s/%s stock=%d ≤ %d",
                    platform.code, product.sku, product.stock, _LOW_STOCK_THRESHOLD,
                )

            # Build pricing context — override strategy to profit_max on low stock
            effective_strategy = (
                PricingStrategy.PROFIT_MAX if stock_is_low
                else PricingStrategy(platform.pricing_strategy)
            )
            trigger_event = "low_stock" if stock_is_low else "competitor_change"

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
                strategy=effective_strategy,
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

            result = await agent.run(ctx, integration, trigger_event=trigger_event)

            # Persist log
            log = PricingAgentLog(
                product_platform_id=pps.id,
                agent_name="PricingAgent",
                trigger_event=trigger_event,
                input_snapshot={
                    "sku": product.sku,
                    "platform_code": platform.code,
                    "strategy": effective_strategy.value,
                    "current_price": float(current_price),
                    "floor_price": float(floor_price),
                    "competitor_price": float(new_min),
                    "old_competitor_price": float(old_min) if old_min else None,
                    "stock": product.stock,
                    "low_stock": stock_is_low,
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
            pps.requires_approval = result.requires_approval

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
                    "confidence_score": log.confidence_score,
                    "is_pending_approval": log.is_pending_approval,
                }
                await self._on_log(log_data, user_id=product.user_id)


    async def _check_own_site(
        self,
        pps: ProductPlatformStatus,
        product: Product,
        platform: Platform,
        session: Any,
    ) -> None:
        """Price own_site using sibling Trendyol/Amazon prices as reference.

        own_site has no marketplace competitors, so we look at the same product's
        current_price on the other platforms and treat those as virtual competitors.
        This lets PROFIT_MAX make informed decisions (e.g. stay above market average).
        """
        # Fetch sibling platform statuses for the same product
        siblings = (
            await session.scalars(
                select(ProductPlatformStatus)
                .join(ProductPlatformStatus.platform)
                .where(
                    ProductPlatformStatus.product_id == pps.product_id,
                    ProductPlatformStatus.id != pps.id,
                    ProductPlatformStatus.status == "listed",
                    ProductPlatformStatus.current_price.isnot(None),
                    Platform.code.in_(["trendyol", "amazon"]),
                )
                .options(selectinload(ProductPlatformStatus.platform))
            )
        ).all()

        if not siblings:
            return  # no other platforms yet — nothing to reference

        virtual_competitors = [
            {
                "seller": f"Pazar-{s.platform.display_name}",
                "price": float(s.current_price),
                "has_buybox": False,
            }
            for s in siblings
        ]
        sibling_prices = [Decimal(str(s.current_price)) for s in siblings]
        cross_platform_ref = (
            sum(sibling_prices, Decimal("0")) / Decimal(len(sibling_prices))
        ).quantize(Decimal("0.01"))

        old_ref = pps.competitor_price
        pps.competitor_price = cross_platform_ref
        pps.has_buybox = True  # own_site always "wins" on its own storefront
        pps.last_synced_at = datetime.now(UTC).replace(tzinfo=None)

        if not _price_changed(old_ref, cross_platform_ref):
            await session.commit()
            return

        logger.info(
            "own_site cross-platform ref changed: %s  ref=%s TL",
            product.sku, cross_platform_ref,
        )

        floor_price = pps.floor_price or compute_floor_price(
            product.base_cost, product.shipping_cost,
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
            virtual_competitors=virtual_competitors,
        )

        settings = get_settings()
        agent = PricingAgent(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            timeout=float(settings.gemini_timeout_seconds),
        )
        integration = _make_integration(platform)
        result = await agent.run(ctx, integration, trigger_event="cross_platform_ref")

        log = PricingAgentLog(
            product_platform_id=pps.id,
            agent_name="PricingAgent",
            trigger_event="cross_platform_ref",
            input_snapshot={
                "sku": product.sku,
                "platform_code": platform.code,
                "strategy": platform.pricing_strategy,
                "current_price": float(current_price),
                "floor_price": float(floor_price),
                "cross_platform_ref": float(cross_platform_ref),
                "virtual_competitors": virtual_competitors,
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
        pps.requires_approval = result.requires_approval

        await session.commit()
        await session.refresh(log)

        if self._on_log is not None and product.user_id is not None:
            await self._on_log({
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
                "confidence_score": log.confidence_score,
                "is_pending_approval": log.is_pending_approval,
            }, user_id=product.user_id)


# ─── Helper ───────────────────────────────────────────────────────────────────

def _price_changed(old: Decimal | None, new: Decimal) -> bool:
    """True if the competitor price moved by at least the threshold."""
    return old is None or abs(new - old) >= _MIN_COMPETITOR_DELTA
