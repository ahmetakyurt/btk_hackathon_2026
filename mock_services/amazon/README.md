# Mock Amazon Service

Standalone FastAPI app simulating Amazon's SP-API surface.

- **Port:** 9002
- **Endpoints (planned, Day 2):** `POST /products`, `PUT /products/{id}/price`, `GET /products/{id}/competitors`, `POST /admin/competitor-price`
- **Storage:** Own SQLite (`mock_amazon.db`)
- **Behavior:** Mid-commission, logistics/turnover-balanced strategy.
