from app.integrations._http_base import HttpBackedMockIntegration


class MockTrendyolService(HttpBackedMockIntegration):
    """HTTP client for the mock Trendyol service running on :9001.

    Drop-in replacement for a future `TrendyolPartnerService` that hits
    Trendyol's real Partner API.
    """

    platform_code = "trendyol"
    commission_rate = 0.20
