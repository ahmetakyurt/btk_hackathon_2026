from __future__ import annotations

from abc import ABC, abstractmethod

from app.integrations.schemas import (
    CompetitorSnapshot,
    ListingPayload,
    ListingResult,
)


class IntegrationError(Exception):
    """Base error for any platform integration failure."""


class IntegrationUnavailableError(IntegrationError):
    """The remote platform did not respond or returned 5xx."""


class ListingNotFoundError(IntegrationError):
    """The remote listing id is unknown."""


class BasePricingIntegration(ABC):
    """Contract every platform integration must implement.

    Both mock services (HTTP clients hitting localhost:90xx) and future
    real-API clients (Trendyol Partner, Amazon SP-API) inherit this.
    The agent layer talks only to this interface, so swapping a mock
    for a real implementation is a one-line change.
    """

    platform_code: str
    commission_rate: float

    @abstractmethod
    async def list_product(self, payload: ListingPayload) -> ListingResult:
        """Publish a product to the platform. (POST /products)"""

    @abstractmethod
    async def update_price(self, external_id: str, price: float) -> bool:
        """Update an existing listing's price. (PUT /products/{id}/price)"""

    @abstractmethod
    async def get_competitor_snapshot(self, external_id: str) -> CompetitorSnapshot:
        """Fetch competitor pricing + buybox state. (GET /products/{id}/competitors)"""

    @abstractmethod
    async def get_listing(self, external_id: str) -> ListingResult | None:
        """Return the current listing state, or None if not found."""
