"""Round-trip tests for the platform HTTP clients.

We mount a tiny inline FastAPI app that mimics the mock-service contract
and run the integration classes against it via httpx ASGI transport. This
proves serialization, parsing, and the platform-specific extra-field hooks
(`fulfillment`, `discount_code`) without spinning real network ports.

Each mock service has its own end-to-end smoke test in
`mock_services/<name>/smoke_test.py` covering buybox & competitor logic.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.integrations.base import IntegrationUnavailableError, ListingNotFoundError
from app.integrations.mock_amazon import MockAmazonService
from app.integrations.mock_own_site import MockOwnSiteService
from app.integrations.mock_trendyol import MockTrendyolService
from app.integrations.schemas import ListingPayload


def _inline_mock_app(*, platform_code: str, has_competitors: bool) -> FastAPI:
    """Build a tiny FastAPI app that records requests and returns canned data."""
    app = FastAPI()
    state: dict[str, Any] = {
        "last_post_body": None,
        "last_put_body": None,
        "listing_price": Decimal("259.00"),
    }
    app.state.recorded = state

    @app.post("/products", status_code=201)
    async def list_product(body: dict[str, Any]) -> dict[str, Any]:
        state["last_post_body"] = body
        state["listing_price"] = Decimal(str(body["price"]))
        return {
            "external_id": "EXT-1",
            "platform_code": platform_code,
            "sku": body["sku"],
            "title": body["title"],
            "description": body.get("description"),
            "category": body.get("category"),
            "listed_price": float(body["price"]),
            "stock": body["stock"],
            "has_buybox": True,
            "status": "listed",
            "listing_url": f"https://mock-{platform_code}.local/p/EXT-1",
        }

    @app.get("/products/{external_id}")
    async def get_listing(external_id: str) -> dict[str, Any]:
        if external_id != "EXT-1":
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="not found")
        return {
            "external_id": external_id,
            "platform_code": platform_code,
            "sku": "SKU-1",
            "title": "Test",
            "description": None,
            "category": None,
            "listed_price": float(state["listing_price"]),
            "stock": 1,
            "has_buybox": True,
            "status": "listed",
            "listing_url": f"https://mock-{platform_code}.local/p/EXT-1",
        }

    @app.put("/products/{external_id}/price")
    async def update_price(external_id: str, body: dict[str, Any]) -> dict[str, Any]:
        if external_id != "EXT-1":
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="not found")
        state["last_put_body"] = body
        state["listing_price"] = Decimal(str(body["price"]))
        return {"ok": True, "external_id": external_id, "new_price": float(body["price"])}

    @app.get("/products/{external_id}/competitors")
    async def get_competitors(external_id: str) -> dict[str, Any]:
        competitors = (
            [{"seller_name": "RivalA", "price": 199.99, "has_buybox": True}]
            if has_competitors
            else []
        )
        return {
            "external_id": external_id,
            "platform_code": platform_code,
            "fetched_at": datetime.utcnow().isoformat(),
            "own_price": float(state["listing_price"]),
            "own_has_buybox": not has_competitors,
            "competitors": competitors,
        }

    return app


def _client_for(app: FastAPI, base_url: str = "http://mock") -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=base_url)


@pytest.fixture
def trendyol_app():
    return _inline_mock_app(platform_code="trendyol", has_competitors=True)


@pytest.fixture
def amazon_app():
    return _inline_mock_app(platform_code="amazon", has_competitors=True)


@pytest.fixture
def own_site_app():
    return _inline_mock_app(platform_code="own_site", has_competitors=False)


# ─── Trendyol ────────────────────────────────────────────────────────────

async def test_trendyol_list_get_update_competitors(trendyol_app):
    async with _client_for(trendyol_app) as client:
        svc = MockTrendyolService("http://mock", client=client)

        listed = await svc.list_product(
            ListingPayload(sku="SKU-1", title="T", description="d", price=Decimal("100"), stock=10)
        )
        assert listed.external_id == "EXT-1"
        assert listed.listed_price == Decimal("100")
        assert "fulfillment" not in trendyol_app.state.recorded["last_post_body"]

        got = await svc.get_listing("EXT-1")
        assert got is not None and got.external_id == "EXT-1"

        ok = await svc.update_price("EXT-1", 95.0)
        assert ok is True
        assert trendyol_app.state.recorded["last_put_body"] == {"price": 95.0}

        snap = await svc.get_competitor_snapshot("EXT-1")
        assert snap.platform_code == "trendyol"
        assert len(snap.competitors) == 1
        assert snap.competitors[0].has_buybox is True
        assert snap.own_has_buybox is False


async def test_trendyol_get_listing_returns_none_on_404(trendyol_app):
    async with _client_for(trendyol_app) as client:
        svc = MockTrendyolService("http://mock", client=client)
        assert await svc.get_listing("NOPE") is None


async def test_trendyol_update_price_404_raises(trendyol_app):
    async with _client_for(trendyol_app) as client:
        svc = MockTrendyolService("http://mock", client=client)
        with pytest.raises(ListingNotFoundError):
            await svc.update_price("NOPE", 50.0)


# ─── Amazon — verifies fulfillment forwarding ───────────────────────────

async def test_amazon_forwards_fulfillment(amazon_app):
    async with _client_for(amazon_app) as client:
        svc = MockAmazonService("http://mock", client=client)
        await svc.list_product(
            ListingPayload(
                sku="SKU-2",
                title="T",
                description="d",
                price=Decimal("50"),
                stock=5,
                raw_specs={"fulfillment": "FBA"},
            )
        )
        body = amazon_app.state.recorded["last_post_body"]
        assert body["fulfillment"] == "FBA"


async def test_amazon_default_fulfillment_is_fbm(amazon_app):
    async with _client_for(amazon_app) as client:
        svc = MockAmazonService("http://mock", client=client)
        await svc.list_product(
            ListingPayload(sku="SKU-2", title="T", description="d", price=Decimal("50"), stock=5)
        )
        assert amazon_app.state.recorded["last_post_body"]["fulfillment"] == "FBM"


# ─── OwnSite — discount_code forwarding + empty-competitors handling ────

async def test_own_site_forwards_discount_code(own_site_app):
    async with _client_for(own_site_app) as client:
        svc = MockOwnSiteService("http://mock", client=client)
        await svc.list_product(
            ListingPayload(
                sku="SKU-3",
                title="T",
                description="d",
                price=Decimal("499"),
                stock=10,
                raw_specs={"discount_code": "WELCOME10"},
            )
        )
        assert own_site_app.state.recorded["last_post_body"]["discount_code"] == "WELCOME10"


async def test_own_site_empty_competitors_snapshot(own_site_app):
    async with _client_for(own_site_app) as client:
        svc = MockOwnSiteService("http://mock", client=client)
        snap = await svc.get_competitor_snapshot("EXT-1")
        assert snap.competitors == []
        assert snap.own_has_buybox is True


# ─── Network failure surfaces as IntegrationUnavailableError ────────────

async def test_integration_unavailable_when_host_unreachable():
    svc = MockTrendyolService("http://127.0.0.1:1")  # almost certainly closed
    with pytest.raises(IntegrationUnavailableError):
        await svc.get_listing("EXT-1")
