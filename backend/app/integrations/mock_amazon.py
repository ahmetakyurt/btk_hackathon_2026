from typing import Any

from app.integrations._http_base import HttpBackedMockIntegration
from app.integrations.schemas import ListingPayload


class MockAmazonService(HttpBackedMockIntegration):
    """HTTP client for the mock Amazon SP-API on :9002.

    Forwards `fulfillment` (FBA/FBM) from raw_specs since Amazon's
    listing endpoint requires it.
    """

    platform_code = "amazon"
    commission_rate = 0.15

    def _extra_listing_fields(self, payload: ListingPayload) -> dict[str, Any]:
        fulfillment = payload.raw_specs.get("fulfillment", "FBM")
        return {"fulfillment": fulfillment}
