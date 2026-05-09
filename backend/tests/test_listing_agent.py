"""Unit tests for ListingAgent and floor price helper."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.agents.listing_agent import ListingAgent, PlatformListing
from app.api.products import compute_floor_price


# ─── compute_floor_price ─────────────────────────────────────────────────────

class TestComputeFloorPrice:
    def test_trendyol_20pct_commission(self) -> None:
        # cost=100, ship=20, commission=0.20, margin=0.05
        # floor = 120 / (1 - 0.20 - 0.05) = 120 / 0.75 = 160.00
        result = compute_floor_price(
            base_cost=Decimal("100"),
            shipping_cost=Decimal("20"),
            commission_rate=Decimal("0.20"),
            min_margin=0.05,
        )
        assert result == Decimal("160.00")

    def test_own_site_2pct_commission(self) -> None:
        # cost=100, ship=20, commission=0.02, margin=0.05
        # floor = 120 / 0.93 ≈ 129.03
        result = compute_floor_price(
            base_cost=Decimal("100"),
            shipping_cost=Decimal("20"),
            commission_rate=Decimal("0.02"),
            min_margin=0.05,
        )
        assert result == Decimal("129.03")

    def test_amazon_15pct_commission(self) -> None:
        # cost=85, ship=15, commission=0.15, margin=0.05
        # floor = 100 / 0.80 = 125.00
        result = compute_floor_price(
            base_cost=Decimal("85"),
            shipping_cost=Decimal("15"),
            commission_rate=Decimal("0.15"),
            min_margin=0.05,
        )
        assert result == Decimal("125.00")

    def test_zero_shipping(self) -> None:
        result = compute_floor_price(
            base_cost=Decimal("200"),
            shipping_cost=Decimal("0"),
            commission_rate=Decimal("0.10"),
            min_margin=0.05,
        )
        # 200 / 0.85 ≈ 235.29
        assert result == Decimal("235.29")

    def test_degenerate_case_returns_double_cost(self) -> None:
        # commission + margin >= 1 → degenerate
        result = compute_floor_price(
            base_cost=Decimal("100"),
            shipping_cost=Decimal("0"),
            commission_rate=Decimal("0.95"),
            min_margin=0.10,
        )
        assert result == Decimal("200.00")


# ─── ListingAgent passthrough ─────────────────────────────────────────────────

class TestListingAgentPassthrough:
    def test_no_api_key_returns_passthrough(self) -> None:
        agent = ListingAgent(api_key="")
        result = ListingAgent._passthrough(
            "trendyol",
            {"sku": "SKU-1", "title": "Test Ürün", "category": "Elektronik"},
        )
        assert result.platform_code == "trendyol"
        assert result.title == "Test Ürün"
        assert isinstance(result.keywords, list)

    @pytest.mark.asyncio
    async def test_generate_listing_falls_back_when_no_key(self) -> None:
        agent = ListingAgent(api_key="")
        result = await agent.generate_listing(
            "trendyol",
            {"sku": "SKU-1", "title": "Bluetooth Kulaklık", "category": "Elektronik"},
        )
        assert isinstance(result, PlatformListing)
        assert result.platform_code == "trendyol"
        assert result.title == "Bluetooth Kulaklık"

    @pytest.mark.asyncio
    async def test_generate_all_platforms_passthrough(self) -> None:
        agent = ListingAgent(api_key="")
        results = await agent.generate_all_platforms(
            ["trendyol", "amazon", "own_site"],
            {"sku": "SKU-2", "title": "Akıllı Saat", "category": "Aksesuar"},
        )
        assert set(results.keys()) == {"trendyol", "amazon", "own_site"}
        for code, listing in results.items():
            assert listing.platform_code == code

    @pytest.mark.asyncio
    async def test_generate_all_handles_partial_failure(self) -> None:
        """Even if one platform's generation fails, others should succeed."""
        agent = ListingAgent(api_key="fake-key-that-will-error")

        # Mock the Gemini call to raise for amazon only
        call_count = 0

        async def fake_generate(platform_code: str, product_info: dict) -> PlatformListing:
            nonlocal call_count
            call_count += 1
            if platform_code == "amazon":
                raise RuntimeError("Simulated Gemini error")
            return PlatformListing(
                platform_code=platform_code,
                title=f"AI Title for {platform_code}",
                description="AI description",
                keywords=["test"],
            )

        import unittest.mock
        with unittest.mock.patch.object(agent, "generate_listing", side_effect=fake_generate):
            results = await agent.generate_all_platforms(
                ["trendyol", "amazon", "own_site"],
                {"sku": "SKU-3", "title": "Base Title", "category": "Test"},
            )

        assert "amazon" in results
        # amazon fell back to passthrough title
        assert results["amazon"].title == "Base Title"
        # others got AI titles
        assert results["trendyol"].title == "AI Title for trendyol"
