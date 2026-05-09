"""Quick TestClient smoke test for the Trendyol mock service.

Run from this directory:
    uv run python smoke_test.py
"""

import os
import sys

os.environ["MOCK_TRENDYOL_DB"] = "sqlite+aiosqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402


def main() -> int:
    with TestClient(app) as client:
        h = client.get("/health").json()
        assert h == {"status": "ok", "platform": "trendyol"}, h

        listed = client.post(
            "/products",
            json={
                "sku": "SKU-1042",
                "title": "Kablosuz Kulaklık X1",
                "description": "Test ürünü",
                "category": "electronics",
                "price": 259.00,
                "stock": 50,
                "keywords": ["kulaklık", "bluetooth"],
            },
        ).json()
        assert listed["status"] == "listed", listed
        ext_id = listed["external_id"]
        assert ext_id.startswith("TY-"), ext_id

        got = client.get(f"/products/{ext_id}").json()
        assert got["sku"] == "SKU-1042", got

        comps = client.get(f"/products/{ext_id}/competitors").json()
        assert len(comps["competitors"]) == 5, comps
        seller_to_drop = comps["competitors"][0]["seller_name"]

        client.put(f"/products/{ext_id}/price", json={"price": 250.00})

        admin = client.post(
            "/admin/competitor-price",
            json={
                "external_id": ext_id,
                "seller_name": seller_to_drop,
                "price": 200.00,
            },
        ).json()
        assert admin["ok"] is True, admin

        comps2 = client.get(f"/products/{ext_id}/competitors").json()
        winner = next(c for c in comps2["competitors"] if c["has_buybox"])
        assert winner["seller_name"] == seller_to_drop, comps2
        assert comps2["own_has_buybox"] is False, comps2

    print("OK — Trendyol mock round-trip + buybox recompute passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
