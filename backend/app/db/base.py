"""Single import surface for Alembic to discover all models."""

from app.db.models import (  # noqa: F401
    Base,
    PricingAgentLog,
    Platform,
    Product,
    ProductPlatformStatus,
)
