"""Tests for CompetitorWatcher and SSE broadcast."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.agents.competitor_watcher import CompetitorWatcher, _price_changed
from app.api.agents import broadcast_log, _subscribers
from app.db.models import Platform, Product, ProductPlatformStatus
from app.integrations.schemas import CompetitorEntry, CompetitorSnapshot


# ─── _price_changed ───────────────────────────────────────────────────────────

class TestPriceChanged:
    def test_none_old_always_triggers(self) -> None:
        assert _price_changed(None, Decimal("100")) is True

    def test_large_delta_triggers(self) -> None:
        assert _price_changed(Decimal("100"), Decimal("95")) is True  # delta=5

    def test_small_delta_no_trigger(self) -> None:
        assert _price_changed(Decimal("100"), Decimal("99.70")) is False  # delta=0.30

    def test_exact_threshold_triggers(self) -> None:
        # threshold is 0.50; delta=0.50 should trigger
        assert _price_changed(Decimal("100"), Decimal("99.50")) is True

    def test_just_below_threshold_no_trigger(self) -> None:
        assert _price_changed(Decimal("100"), Decimal("99.51")) is False  # delta=0.49


# ─── broadcast_log / SSE queue ────────────────────────────────────────────────

class TestBroadcastLog:
    @pytest.mark.asyncio
    async def test_message_reaches_subscriber(self) -> None:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        _subscribers.append(q)
        try:
            await broadcast_log({"type": "test", "value": 42})
            data = q.get_nowait()
            assert data == {"type": "test", "value": 42}
        finally:
            _subscribers.remove(q)

    @pytest.mark.asyncio
    async def test_full_queue_is_dropped_gracefully(self) -> None:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=1)
        q.put_nowait({"first": True})  # fill the queue
        _subscribers.append(q)
        try:
            # Should not raise even though queue is full
            await broadcast_log({"second": True})
            # Subscriber should have been removed (dead queue)
            assert q not in _subscribers
        finally:
            if q in _subscribers:
                _subscribers.remove(q)

    @pytest.mark.asyncio
    async def test_no_subscribers_is_safe(self) -> None:
        # Should not raise with no subscribers at all
        await broadcast_log({"orphan": True})


# ─── CompetitorWatcher integration ───────────────────────────────────────────

class TestCompetitorWatcher:
    """Tests using in-memory SQLite + mocked integrations."""

    @pytest.fixture
    async def db_session(self) -> AsyncSession:
        test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        from app.db.base import Base  # noqa: F401
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            yield session
        await test_engine.dispose()

    async def _seed_db(self, session: AsyncSession) -> ProductPlatformStatus:
        platform = Platform(
            code="trendyol",
            display_name="Trendyol",
            commission_rate=Decimal("0.2000"),
            base_url="http://localhost:9001",
            pricing_strategy="buybox",
            is_active=True,
        )
        product = Product(
            sku="SKU-W1",
            title="Test Ürün",
            base_cost=Decimal("120"),
            shipping_cost=Decimal("20"),
            stock=50,
            category="Test",
        )
        session.add_all([platform, product])
        await session.flush()

        pps = ProductPlatformStatus(
            product_id=product.id,
            platform_id=platform.id,
            external_id="TY-00000001",
            current_price=Decimal("260"),
            floor_price=Decimal("200"),
            ceiling_price=Decimal("400"),
            competitor_price=Decimal("258"),
            status="listed",
        )
        session.add(pps)
        await session.commit()
        await session.refresh(pps)
        return pps

    def _mock_snapshot(self, prices: list[float], own_has_buybox: bool = False) -> CompetitorSnapshot:
        return CompetitorSnapshot(
            external_id="TY-00000001",
            platform_code="trendyol",
            competitors=[
                CompetitorEntry(seller_name=f"Seller{i}", price=Decimal(str(p)))
                for i, p in enumerate(prices)
            ],
            fetched_at=datetime.now(UTC),
            own_has_buybox=own_has_buybox,
            own_price=Decimal("260"),
        )

    @pytest.mark.asyncio
    async def test_no_trigger_when_delta_below_threshold(self, db_session: AsyncSession) -> None:
        """Competitor moves only 0.30 TL — PricingAgent must NOT be called."""
        await self._seed_db(db_session)

        integration = AsyncMock()
        # old competitor_price = 258; new min = 257.70 → delta = 0.30 < threshold
        integration.get_competitor_snapshot = AsyncMock(
            return_value=self._mock_snapshot([257.70, 260.0])
        )
        integration.update_price = AsyncMock(return_value=True)

        logs_received: list[dict] = []

        with patch("app.agents.competitor_watcher._make_integration", return_value=integration), \
             patch("app.agents.competitor_watcher.SessionLocal") as mock_sl:
            mock_sl.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_sl.return_value.__aexit__ = AsyncMock(return_value=False)

            watcher = CompetitorWatcher(poll_interval=5, on_log=lambda d: logs_received.append(d) or asyncio.sleep(0))
            await watcher._poll_once()

        # No log should have been broadcast (no agent triggered)
        assert len(logs_received) == 0
        integration.update_price.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_trigger_when_no_competitors(self, db_session: AsyncSession) -> None:
        """own_site style — empty competitor list → watcher skips."""
        await self._seed_db(db_session)

        integration = AsyncMock()
        integration.get_competitor_snapshot = AsyncMock(
            return_value=CompetitorSnapshot(
                external_id="TY-00000001",
                platform_code="trendyol",
                competitors=[],  # no competitors
                fetched_at=datetime.now(UTC),
                own_has_buybox=True,
            )
        )

        logs_received: list[dict] = []

        with patch("app.agents.competitor_watcher._make_integration", return_value=integration), \
             patch("app.agents.competitor_watcher.SessionLocal") as mock_sl:
            mock_sl.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_sl.return_value.__aexit__ = AsyncMock(return_value=False)

            watcher = CompetitorWatcher(poll_interval=5, on_log=lambda d: logs_received.append(d) or asyncio.sleep(0))
            await watcher._poll_once()

        assert len(logs_received) == 0

    @pytest.mark.asyncio
    async def test_watcher_start_stop(self) -> None:
        """start() loops; stop() + cancel terminates cleanly."""
        watcher = CompetitorWatcher(poll_interval=60)

        async def fake_poll():
            pass

        watcher._poll_once = fake_poll  # type: ignore[method-assign]
        task = asyncio.create_task(watcher.start())
        await asyncio.sleep(0.05)  # let at least one loop run
        watcher.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        assert not watcher._running
