from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class ProductCreateRequest(BaseModel):
    sku: str = Field(..., min_length=1, max_length=64)
    title: str = Field(..., min_length=1, max_length=255)
    base_cost: Decimal = Field(..., gt=0)
    shipping_cost: Decimal = Field(..., ge=0)
    stock: int = Field(..., ge=0)
    category: str | None = None
    raw_specs: dict[str, Any] = Field(default_factory=dict)
    # Initial listing price; defaults to cost+shipping + 30% margin if omitted
    initial_price: Decimal | None = None


class PlatformStatusOut(BaseModel):
    id: int
    platform_code: str
    platform_name: str
    external_id: str | None
    current_price: float | None
    floor_price: float | None
    competitor_price: float | None
    ai_generated_title: str | None
    has_buybox: bool
    status: str
    error_message: str | None = None


class ProductOut(BaseModel):
    id: int
    sku: str
    title: str
    base_cost: float
    shipping_cost: float
    stock: int
    category: str | None
    created_at: datetime
    platform_statuses: list[PlatformStatusOut]
