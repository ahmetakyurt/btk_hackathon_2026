from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ListingPayload(BaseModel):
    """Input contract for publishing a product to a platform."""

    sku: str
    title: str
    description: str
    category: str | None = None
    price: Decimal
    stock: int
    keywords: list[str] = Field(default_factory=list)
    raw_specs: dict[str, str] = Field(default_factory=dict)


class ListingResult(BaseModel):
    """Result of a successful listing action."""

    external_id: str
    platform_code: str
    listed_price: Decimal
    status: str  # 'listed' | 'pending' | 'rejected'
    listing_url: str | None = None


class CompetitorEntry(BaseModel):
    seller_name: str
    price: Decimal
    has_buybox: bool = False


class CompetitorSnapshot(BaseModel):
    """Snapshot of competitor pricing for a single listing."""

    external_id: str
    platform_code: str
    competitors: list[CompetitorEntry]
    fetched_at: datetime
    own_has_buybox: bool = False
    own_price: Decimal | None = None
