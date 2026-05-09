# Mock Trendyol Service

Standalone FastAPI app simulating Trendyol's seller API.

- **Port:** 9001
- **Endpoints (planned, Day 2):** `POST /products`, `PUT /products/{id}/price`, `GET /products/{id}/competitors`, `POST /admin/competitor-price`
- **Storage:** Own SQLite (`mock_trendyol.db`)
- **Behavior:** Mimics Trendyol's high-commission, buybox-driven marketplace.
