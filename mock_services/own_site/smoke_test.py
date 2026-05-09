"""Smoke test for the OwnSite mock. Run: uv run python smoke_test.py"""

import os
import sys

os.environ["MOCK_OWN_SITE_DB"] = "sqlite+aiosqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402


def main() -> int:
    with TestClient(app) as client:
        h = client.get("/health").json()
        assert h == {"status": "ok", "platform": "own_site"}, h

        listed = client.post(
            "/products",
            json={
                "sku": "SKU-3001",
                "title": "Premium Hediye Seti",
                "description": "Marka hikayesi",
                "category": "lifestyle",
                "price": 499.00,
                "stock": 30,
                "discount_code": "WELCOME10",
            },
        ).json()
        assert listed["status"] == "listed", listed
        assert listed["external_id"].startswith("OWN-"), listed
        assert listed["has_buybox"] is True, listed

        comps = client.get(f"/products/{listed['external_id']}/competitors").json()
        assert comps["competitors"] == [], comps
        assert comps["own_has_buybox"] is True, comps

        admin_resp = client.post(
            "/admin/competitor-price",
            json={"external_id": "x", "seller_name": "y", "price": 1},
        )
        assert admin_resp.status_code == 410, admin_resp.text

    print("OK — OwnSite mock round-trip + no-competitor invariant passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
