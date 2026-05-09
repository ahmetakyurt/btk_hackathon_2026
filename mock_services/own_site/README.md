# Mock Own Site Service

Standalone FastAPI app simulating the seller's own storefront (Shopify/Next.js style).

- **Port:** 9003
- **Endpoints (planned, Day 2):** `POST /products`, `PUT /products/{id}/price`, `GET /products/{id}/competitors`, `POST /admin/competitor-price`
- **Storage:** Own SQLite (`mock_own_site.db`)
- **Behavior:** Low-commission, profit-maximizing pricing strategy.
