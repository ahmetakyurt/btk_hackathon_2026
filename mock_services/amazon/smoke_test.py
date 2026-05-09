"""Smoke test for the Amazon mock. Run: uv run python smoke_test.py"""

import os
import sys

os.environ["MOCK_AMAZON_DB"] = "sqlite+aiosqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402


def main() -> int:
    with TestClient(app) as client:
        h = client.get("/health").json()
        assert h == {"status": "ok", "platform": "amazon"}, h

        listed = client.post(
            "/products",
            json={
                "sku": "SKU-2001",
                "title": "Wireless Earbuds X1",
                "description": "Test product",
                "category": "electronics",
                "price": 29.99,
                "stock": 100,
                "fulfillment": "FBA",
            },
        ).json()
        assert listed["status"] == "listed", listed
        ext_id = listed["external_id"]
        assert ext_id.startswith("B0") and len(ext_id) == 10, ext_id
        assert listed["fulfillment"] == "FBA", listed

        comps = client.get(f"/products/{ext_id}/competitors").json()
        assert len(comps["competitors"]) == 4, comps

        # Drop one competitor's price below ours; they should win buybox.
        seller = comps["competitors"][0]["seller_name"]
        client.post(
            "/admin/competitor-price",
            json={
                "external_id": ext_id,
                "seller_name": seller,
                "price": 1.00,
            },
        )
        comps2 = client.get(f"/products/{ext_id}/competitors").json()
        winner = next(c for c in comps2["competitors"] if c["has_buybox"])
        assert winner["seller_name"] == seller, comps2

        # Update our own price below all competitors → we win back buybox.
        client.put(f"/products/{ext_id}/price", json={"price": 0.50})
        comps3 = client.get(f"/products/{ext_id}/competitors").json()
        assert comps3["own_has_buybox"] is True, comps3

    print("OK — Amazon mock round-trip + ASIN + buybox passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
