# OptiPrice AI

> **BTK Akademi × Google × Girvak — Shackathon'26**
> Multi-channel autonomous pricing & listing agent for e-commerce sellers.

OptiPrice AI is a B2B/SaaS control panel that lets a seller define a product **once** — OptiPrice then:

1. **Lists** it on Trendyol, Amazon, and the seller's own storefront with **platform-tailored AI-generated copy** (Gemini Structured Outputs)
2. **Watches** competitor prices every 5 seconds via an async polling loop
3. **Re-prices autonomously** under cost / commission / shipping constraints using a **Gemini Function Calling agent loop**
4. **Streams every decision** to a live terminal-style transparency dashboard (SSE)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend: Next.js 16 (App Router) + TypeScript + Tailwind CSS  │
│  /products  /logs (SSE live terminal)  /simulator (jury demo)   │
└──────────────────────────┬──────────────────────────────────────┘
                           │ REST / SSE
┌──────────────────────────▼──────────────────────────────────────┐
│  Backend Core API: FastAPI (Python 3.14, async)                  │
│  /api/products  /api/pricing  /api/agents/logs/stream  /api/sim  │
└──┬──────────────┬──────────────┬──────────────┬─────────────────┘
   │              │              │              │
┌──▼──────┐  ┌───▼──────┐  ┌───▼────────┐  ┌──▼──────────────────┐
│ Listing │  │ Pricing  │  │ Competitor │  │ Mock Platform Svcs  │
│  Agent  │  │  Agent   │  │  Watcher   │  │  Trendyol  :9001    │
│(Gemini  │  │(Gemini   │  │(async 5s   │  │  Amazon    :9002    │
│Struct.  │  │Function  │  │  poll)     │  │  OwnSite   :9003    │
│Output)  │  │Calling)  │  │            │  │  (FastAPI + SQLite) │
└─────────┘  └──────────┘  └────────────┘  └─────────────────────┘
                  │                               │
                  └───────────────────────────────┘
                                  │
                      ┌───────────▼──────────┐
                      │  SQLite + SQLAlchemy  │
                      │  (PostgreSQL-ready)   │
                      └──────────────────────┘
```

### Agent Design

| Agent | Trigger | Model | Method |
|---|---|---|---|
| **ListingAgent** | "Send to all platforms" button | Gemini 2.0 Flash | Structured Outputs (JSON Schema) |
| **PricingAgent** | Competitor price change / manual | Gemini 2.0 Flash | Function Calling loop (max 6 turns) |
| **CompetitorWatcher** | Always-on async loop | — | httpx polling every 5s |

### Platform Pricing Strategies

| Platform | Commission | Strategy | Logic |
|---|---|---|---|
| Trendyol | 20% | `buybox` | Undercut lowest competitor by 0.50 TL (floor-protected) |
| Amazon | 15% | `logistics_balance` | Stay near competitor average |
| Own Site | 2% | `profit_max` | Maximize margin; 5% below competitor if one exists |

---

## Tech Stack

**Backend:** Python 3.14, FastAPI, SQLAlchemy 2 (async), Alembic, httpx, Pydantic v2, google-genai 2.0  
**Frontend:** Next.js 16, React 19, TypeScript 5.9, Tailwind CSS 4, react-hook-form + zod  
**AI:** Gemini 2.0 Flash — Structured Outputs for listing, Function Calling for pricing  
**Storage:** SQLite (dev) → PostgreSQL-ready schema  
**Package managers:** uv (Python), pnpm (Node)

---

## Quickstart

### Prerequisites

- Python 3.11+ (tested on 3.14)
- Node.js 20+
- [uv](https://docs.astral.sh/uv/) — fast Python package manager
- [pnpm](https://pnpm.io/) — Node package manager
- A [Gemini API key](https://aistudio.google.com/app/apikey) (free tier is enough)

### 1. Clone & configure

```bash
git clone <repo-url> optiprice
cd optiprice
cp .env.example .env   # Windows: copy .env.example .env
# Edit .env and set GEMINI_API_KEY=your_key_here
```

### 2. Mock platform services (3 separate terminals)

```bash
cd mock_services/trendyol && uv sync && uv run uvicorn main:app --port 9001
cd mock_services/amazon   && uv sync && uv run uvicorn main:app --port 9002
cd mock_services/own_site && uv sync && uv run uvicorn main:app --port 9003
```

### 3. Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --port 8000
# DB is auto-created on first run (SQLAlchemy create_all)
```

### 4. Frontend

```bash
cd frontend
pnpm install
pnpm dev   # http://localhost:3000
```

### 5. Seed demo data (optional)

```bash
cd backend
python seed_demo.py
# Creates 5 products: Sony, Philips, Xiaomi, Tefal, Logitech — listed on all 3 platforms
```

---

## Key Features

### Multi-Platform Listing
One product definition → three platform-specific AI descriptions generated in parallel. Gemini adapts tone per platform: SEO/keyword-heavy for Trendyol, bullet-point technical for Amazon, brand storytelling for the seller's own site.

### Autonomous Re-pricing
The PricingAgent runs a Gemini Function Calling loop:
1. `get_competitor_prices` — fetch live competitor snapshot
2. `calculate_floor_price` — compute cost + shipping + commission floor
3. Strategy decision (buybox / logistics_balance / profit_max)
4. `update_platform_price` — apply new price if delta > 0.50 TL
5. `log_decision` — write audit log

Floor protection: if the target price would drop below `(cost + shipping) / (1 - commission - 5% margin)`, the agent logs `floor_hit` and holds at the floor price — never sells at a loss.

### Live Log Dashboard
Every agent decision streams to a terminal-style SSE panel in real time:
```
[12:04:33] PricingAgent · Trendyol / SONY-WH1000XM5 · competitor_change
  ▸ tool: get_competitor_prices()  → 3890.00 TL (was 4100.00)
  ▸ tool: calculate_floor_price()  → 3780.00 TL
  ↳ reasoning: Strateji buybox: 3967 → 3889.50 TL (5 rakip, floor 3780 TL).
  ↳ DECISION: price_updated (3967.05 → 3889.50 ₺) in 1340ms
```

### Competitor Simulator (Jury Demo)
A panel at `/simulator` lets anyone change competitor prices live. The CompetitorWatcher detects the change within 5 seconds, the PricingAgent responds autonomously, and the decision streams to the live log panel — all visible in real time.

---

## Project Structure

```
bkt_hackathon_2026/
├── CLAUDE.md                    # project constitution + dev log
├── backend/
│   ├── app/
│   │   ├── agents/              # ListingAgent, PricingAgent, CompetitorWatcher
│   │   ├── api/                 # products, pricing, agents (SSE), simulator
│   │   ├── db/                  # SQLAlchemy models + session
│   │   ├── integrations/        # BasePricingIntegration + 3 mock clients
│   │   └── schemas/
│   └── seed_demo.py             # demo data seed script
├── mock_services/
│   ├── trendyol/                # :9001 — buybox, 5 competitors, [-8%,+8%] band
│   ├── amazon/                  # :9002 — ASIN IDs, 4 competitors, FBA/FBM
│   └── own_site/                # :9003 — no competitors, profit_max
└── frontend/
    ├── src/app/
    │   ├── products/            # list + new + [id] detail
    │   ├── logs/                # SSE live terminal
    │   └── simulator/           # competitor price editor
    └── src/lib/api.ts           # typed API client + domain types
```

---

## Submission

**Competition:** BTK Akademi × Google × Girvak — Shackathon'26  
**Deadline:** 19 May 2026, 23:59  
**Team:** ahmetakyurt
