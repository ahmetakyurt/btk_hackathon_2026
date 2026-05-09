from typing import Any

from app.integrations._http_base import HttpBackedMockIntegration
from app.integrations.schemas import ListingPayload


class MockOwnSiteService(HttpBackedMockIntegration):
    """HTTP client for the seller's own storefront on :9003.

    Forwards an optional `discount_code` from raw_specs. The storefront
    has no competitors, so `get_competitor_snapshot` returns an empty
    list with `own_has_buybox=True`.
    """

    platform_code = "own_site"
    commission_rate = 0.02

    def _extra_listing_fields(self, payload: ListingPayload) -> dict[str, Any]:
        code = payload.raw_specs.get("discount_code")
        return {"discount_code": code} if code else {}
