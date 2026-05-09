"""Shared httpx-backed implementation of `BasePricingIntegration`.

All three mock services (and, later, the real Trendyol/Amazon clients that
swap in without touching the agent layer) speak the same shape:

  POST /products                          → list a product
  PUT  /products/{external_id}/price      → update price
  GET  /products/{external_id}            → fetch listing
  GET  /products/{external_id}/competitors → fetch competitor snapshot

This base class implements all four methods over httpx. Per-platform
clients only need to set `platform_code`, `commission_rate`, and
optionally extend `_extra_listing_fields` to forward platform-specific
attributes (e.g. Amazon's `fulfillment`).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

import httpx

from app.integrations.base import (
    BasePricingIntegration,
    IntegrationUnavailableError,
    ListingNotFoundError,
)
from app.integrations.schemas import (
    CompetitorEntry,
    CompetitorSnapshot,
    ListingPayload,
    ListingResult,
)


class HttpBackedMockIntegration(BasePricingIntegration):
    """Concrete HTTP integration shared by all 3 mock services.

    Subclasses should set:
        platform_code: str
        commission_rate: float
    and optionally override `_extra_listing_fields` to inject
    platform-specific request body fields.
    """

    platform_code: str = ""
    commission_rate: float = 0.0

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 10.0,
        client: httpx.AsyncClient | None = None,
    ):
        if not self.platform_code:
            raise ValueError(f"{type(self).__name__}.platform_code must be set")
        self.base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._injected_client = client

    # ─── Hook for platform-specific listing fields ─────────────────────

    def _extra_listing_fields(self, payload: ListingPayload) -> dict[str, Any]:
        """Override in subclasses to add fields like `fulfillment` or `discount_code`.

        Default: pull them out of `raw_specs` if present.
        """
        return {}

    # ─── Internal helpers ──────────────────────────────────────────────

    async def _request(self, method: str, path: str, **kw: Any) -> httpx.Response:
        if self._injected_client is not None:
            return await self._injected_client.request(method, path, **kw)
        async with httpx.AsyncClient(
            base_url=self.base_url, timeout=self._timeout
        ) as client:
            try:
                return await client.request(method, path, **kw)
            except httpx.RequestError as e:
                raise IntegrationUnavailableError(
                    f"{self.platform_code}: {e!s}"
                ) from e

    @staticmethod
    def _parse_listing(data: dict[str, Any]) -> ListingResult:
        return ListingResult(
            external_id=str(data["external_id"]),
            platform_code=data.get("platform_code", ""),
            listed_price=Decimal(str(data["listed_price"])),
            status=data["status"],
            listing_url=data.get("listing_url"),
        )

    # ─── BasePricingIntegration impl ───────────────────────────────────

    async def list_product(self, payload: ListingPayload) -> ListingResult:
        body: dict[str, Any] = {
            "sku": payload.sku,
            "title": payload.title,
            "description": payload.description,
            "category": payload.category,
            "price": float(payload.price),
            "stock": payload.stock,
            "keywords": payload.keywords,
        }
        body.update(self._extra_listing_fields(payload))

        resp = await self._request("POST", "/products", json=body)
        if resp.status_code >= 500:
            raise IntegrationUnavailableError(
                f"{self.platform_code}: POST /products → {resp.status_code}"
            )
        if resp.status_code != 201:
            raise IntegrationUnavailableError(
                f"{self.platform_code}: POST /products failed: {resp.status_code} {resp.text}"
            )
        return self._parse_listing(resp.json())

    async def update_price(self, external_id: str, price: float) -> bool:
        resp = await self._request(
            "PUT", f"/products/{external_id}/price", json={"price": price}
        )
        if resp.status_code == 404:
            raise ListingNotFoundError(
                f"{self.platform_code}: listing {external_id} not found"
            )
        if resp.status_code >= 500:
            raise IntegrationUnavailableError(
                f"{self.platform_code}: PUT price → {resp.status_code}"
            )
        return bool(resp.json().get("ok", False))

    async def get_competitor_snapshot(self, external_id: str) -> CompetitorSnapshot:
        resp = await self._request("GET", f"/products/{external_id}/competitors")
        if resp.status_code == 404:
            raise ListingNotFoundError(
                f"{self.platform_code}: listing {external_id} not found"
            )
        if resp.status_code >= 500:
            raise IntegrationUnavailableError(
                f"{self.platform_code}: GET competitors → {resp.status_code}"
            )
        data = resp.json()
        return CompetitorSnapshot(
            external_id=data["external_id"],
            platform_code=data.get("platform_code", self.platform_code),
            fetched_at=datetime.fromisoformat(data["fetched_at"]),
            own_price=Decimal(str(data["own_price"])),
            own_has_buybox=bool(data.get("own_has_buybox", False)),
            competitors=[
                CompetitorEntry(
                    seller_name=c["seller_name"],
                    price=Decimal(str(c["price"])),
                    has_buybox=bool(c.get("has_buybox", False)),
                )
                for c in data.get("competitors", [])
            ],
        )

    async def get_listing(self, external_id: str) -> ListingResult | None:
        resp = await self._request("GET", f"/products/{external_id}")
        if resp.status_code == 404:
            return None
        if resp.status_code >= 500:
            raise IntegrationUnavailableError(
                f"{self.platform_code}: GET listing → {resp.status_code}"
            )
        return self._parse_listing(resp.json())
