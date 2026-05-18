# OptiPrice AI

> **BTK Akademi × Google × GİRVAK — Hackathon'26**
> Autonomous multi-channel pricing & listing agent for e-commerce sellers.

OptiPrice AI is a B2B/SaaS control panel that lets a seller define a product **once** — then Gemini-powered agents:

1. **List** it on Trendyol, Amazon, and the seller's own storefront with **platform-tailored AI copy** (Gemini Structured Outputs)
2. **Watch** competitor prices via an async polling loop (configurable interval)
3. **Re-price autonomously** under cost / commission / floor constraints using a **Gemini Function Calling agent loop** — with a deterministic fallback that keeps pricing alive even if Gemini quota is exhausted
4. **Hold for human approval** when confidence score drops below threshold (Human-in-the-Loop)
5. **Stream every decision** to a live terminal-style transparency dashboard (SSE)

---

## For Jury — Test Etmek İçin

Sistemi kurmadan canlı deploy üzerinden test edebilirsiniz:

- **Uygulama:** https://optiprice.online *(landing → "Hemen Başla")*
- **Demo video:** https://youtu.be/BTUeaO8MFFQ *(~60 saniye — problem, çözüm, canlı ajan kararı, deterministik fallback, iş modeli)*
- **Demo hesabı:** `jury@optiprice.online` / `OptiPrice2026!`
  *(veya kendi hesabınızı 10 saniyede oluşturabilirsiniz — e-posta doğrulaması yok)*

**Önerilen test akışı (~2 dakika):**

1. Giriş yapın → **Ürünler** sayfasında **"Demo Verisini Yükle"** butonuna basın *(10 ürün, 3 platforma listelenir)*.
2. Bir ürüne tıklayın → 3 platform kartında AI üretilmiş başlık/açıklama, güncel fiyat, buybox durumu, son ajan kararı.
3. Sol menü → **Rakip Simülatörü** → bir rakibin fiyatını ~%15 düşürüp **Güncelle**.
4. Sol menü → **Canlı Loglar** → 20 saniye içinde PricingAgent'ın kararı SSE üzerinden akacak (tool çağrıları, Türkçe gerekçe, confidence skoru).
5. **Dashboard** → platform bazlı kâr, buybox oranı, Gemini destekli aksiyon önerileri.

**Not — Rakip Simülatörü hakkında:** `/simulator` sayfası **demo amaçlı bir test aracıdır**, ürünün kalıcı bir özelliği değildir. Hackathon kapsamında gerçek Trendyol Partner / Amazon SP-API entegrasyonları yapılamadığı için mock pazaryeri servisleri kullanıyoruz; jürinin "rakip fiyatını düşürünce ajan ne yapar" senaryosunu canlı görebilmesi için simülatör bu mock servislere doğrudan müdahale etme imkânı veriyor. Gerçek API'lerle entegre edilen prodüksiyon sürümünde bu sayfa yerini canlı rakip izleme paneline bırakacaktır. Mimari hazır: `BasePricingIntegration` abstract class'ı sayesinde mock servisleri gerçek entegrasyonlarla değiştirmek tek dosya değişimi mesafesinde.

**Not — API kotası tükenirse:** PricingAgent **dual-path** tasarımdadır. Gemini erişilemezse deterministik fallback otomatik devreye girer; sistem aynı kararları kural tabanlı verir, sadece doğal dil gerekçe kaybolur. Yani test sırasında kota tükense bile demo çalışmaya devam eder.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  Frontend: Next.js 16 (App Router) · TypeScript · Tailwind CSS   │
│  /products  /logs (SSE live terminal)  /simulator  /dashboard    │
└──────────────────────────┬───────────────────────────────────────┘
                           │ REST / SSE
┌──────────────────────────▼───────────────────────────────────────┐
│  Backend: FastAPI (Python 3.12, async)                            │
│  /api/products  /api/pricing  /api/agents/logs/stream  /api/sim   │
└──┬──────────────┬──────────────┬──────────────┬──────────────────┘
   │              │              │              │
┌──▼──────┐  ┌───▼──────┐  ┌───▼────────┐  ┌──▼──────────────────┐
│ Listing │  │ Pricing  │  │ Competitor │  │ Mock Platform Svcs  │
│  Agent  │  │  Agent   │  │  Watcher   │  │  Trendyol  :9001    │
│(Gemini  │  │(Gemini   │  │(20s poll,  │  │  Amazon    :9002    │
│Struct.  │  │FnCalling)│  │            │  │  OwnSite   :9003    │
│Output)  │  │          │  │            │  │  (FastAPI + SQLite) │
└─────────┘  └──────────┘  └────────────┘  └─────────────────────┘
                  │                               │
                  └───────────────────────────────┘
                                  │
                      ┌───────────▼──────────┐
                      │  Supabase Postgres   │
                      │  (asyncpg, RLS)      │
                      └──────────────────────┘
```

### Agent Design

| Agent | Trigger | Model | Method |
|---|---|---|---|
| **ListingAgent** | Product save | Gemini 2.5 Flash | Structured Outputs — 3 platforms in parallel |
| **PricingAgent** | Competitor change / manual / low stock | Gemini 2.5 Flash | Function Calling loop (max 6 turns) |
| **CompetitorWatcher** | Always-on async loop | — | httpx polling every 20s (configurable via `COMPETITOR_POLL_INTERVAL_SECONDS`) |
| **SalesAssistant** | User question | Gemini 2.5 Flash | Single-shot with product + log context |
| **InsightsAgent** | Dashboard load | Gemini 2.5 Flash | Analytics summary → actionable suggestions |

### Platform Pricing Strategies

| Platform | Commission | Strategy | Logic |
|---|---|---|---|
| Trendyol | 20% | `buybox` | If we have buybox: raise to 0.50 ₺ above 2nd cheapest. If lost: undercut winner by 0.50 ₺ |
| Amazon | 15% | `logistics_balance` | Stay near competitor **median** (outlier-resistant) |
| Own Site | 2% | `profit_max` | We have buybox: raise 5% toward ceiling. Lost: 5% below reference competitor. Uses **cross-platform reference** — sibling Trendyol/Amazon prices injected as virtual competitors since own_site has no marketplace rivals |

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 16 (App Router), TypeScript, Tailwind CSS, Shadcn UI, Recharts |
| **Backend** | FastAPI (Python 3.12), SQLAlchemy 2.0 (async), Pydantic v2, asyncpg |
| **Database** | Supabase Postgres with Row Level Security |
| **AI / Agents** | Google Gemini 2.5 Flash — Function Calling + Structured Outputs |
| **Auth** | NextAuth v5 (JWT cookies), bcrypt, password reset via Resend |
| **Realtime** | SSE (Server-Sent Events), per-user queues, auto-reconnect |
| **Deploy** | Railway (backend + mock services), Vercel (frontend) |

---

## Quickstart

### Prerequisites

- Python 3.12+
- Node.js 20+
- [pnpm](https://pnpm.io/)
- A [Gemini API key](https://aistudio.google.com/app/apikey)
- A Supabase project (or adapt `DATABASE_URL` to a local Postgres)

### 1. Clone & configure

```bash
git clone <repo-url> optiprice
cd optiprice
cp backend/.env.example backend/.env
# Set GEMINI_API_KEY, DATABASE_URL, NEXTAUTH_SECRET, etc.
```

### 2. Mock platform services (combined — single port)

```bash
cd mock_services/combined
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt  # macOS/Linux
.venv/Scripts/uvicorn main:app --port 9000
```

Exposes three routers: `/trendyol`, `/amazon`, `/own_site` — all on port 9000.

### 3. Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
.venv/Scripts/uvicorn app.main:app --port 8000
# Swagger UI: http://localhost:8000/docs
```

### 4. Frontend

```bash
cd frontend
pnpm install
pnpm dev   # http://localhost:3000
```

### 5. Seed demo data (optional)

Use the **"Demo verisini yükle"** button on the empty products page — or run:

```bash
cd backend
python seed_demo.py --user-id 1
# Creates 5 products: Sony, Philips, Xiaomi, Tefal, Logitech
```

### Docker Compose (all services)

```bash
docker compose build --no-cache && docker compose up
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000/docs
```

---

## Environment Variables

**Backend `backend/.env`:**
```
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db
NEXTAUTH_SECRET=...
RESEND_API_KEY=...
RESEND_FROM_EMAIL=noreply@yourdomain.com
APP_PUBLIC_URL=http://localhost:3000
MOCK_TRENDYOL_URL=http://localhost:9000/trendyol
MOCK_AMAZON_URL=http://localhost:9000/amazon
MOCK_OWN_SITE_URL=http://localhost:9000/own_site
COMPETITOR_POLL_INTERVAL_SECONDS=20
PRICING_AGENT_MIN_MARGIN=0.05
GEMINI_TIMEOUT_SECONDS=15
```

**Frontend `frontend/.env.local`:**
```
AUTH_SECRET=...          # same value as NEXTAUTH_SECRET
BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

---

## Key Features

### Multi-Platform Listing
One product → three platform-specific AI descriptions generated in parallel via `asyncio.gather`. Gemini adapts tone per platform: SEO/keyword-heavy for Trendyol, bullet-point technical for Amazon, brand storytelling for the seller's own site.

### Autonomous Re-pricing with Floor Protection
PricingAgent runs a Gemini Function Calling loop:
1. `get_competitor_prices` — fetch live snapshot from mock service
2. `calculate_floor_price` — `(cost + shipping) / (1 - commission - 5% margin)`
3. Strategy decision (buybox / logistics_balance / profit_max) with outlier detection
4. `update_platform_price` — apply if Δ > 0.50 ₺ and above floor
5. `log_decision` — write audit log with full reasoning

### Human-in-the-Loop
Confidence score computed on every `update_platform_price` call. Score < 75 → `PENDING_APPROVAL` decision: price is held, user sees "⚠ ONAY BEKLİYOR" badge in the live log and can Approve or Reject inline.

### Live Log Dashboard
Every agent decision streams to a terminal-style SSE panel:
```
[14:22:11] PricingAgent · Trendyol / SONY-WH1000XM5 · competitor_change
  ▸ tool: get_competitor_prices()  → 3890.00 ₺ (was 4100.00)
  ▸ tool: calculate_floor_price()  → 3780.00 ₺
  ↳ reasoning: Buybox bizde; 2. en ucuz rakip 3967 ₺ → 0.50 ₺ üstüne çıkıyorum.
  ↳ DECISION: price_updated (3967.05 → 3967.50 ₺)  confidence: 91  18340ms
```

### Agent Reasoning Card
Each platform card on the product detail page shows an expandable "Last Agent Decision" section: decision badge, confidence bar, full Gemini Turkish reasoning, tool call list, price delta, and duration.

### Competitor Simulator (Jury Demo)
`/simulator` lets anyone change competitor prices live. CompetitorWatcher detects the change on its next tick (default 20s), PricingAgent responds autonomously, and the decision streams to the live log — all visible in real time. The simulator also syncs buybox state to the DB immediately for instant UI feedback.

### AI Insights
Dashboard shows 3-5 prioritized Gemini-generated action suggestions based on the last 24 hours of logs and current buybox/stock state. Rule-based fallback if Gemini is unavailable.

### Stock-Based Pricing
When a product's stock drops to ≤ 10 units, CompetitorWatcher automatically triggers PricingAgent with `profit_max` strategy override and a 1-hour cooldown to prevent spam.

---

## Project Structure

```
optiprice/
├── backend/
│   ├── app/
│   │   ├── agents/          # listing_agent.py, pricing_agent.py, competitor_watcher.py
│   │   ├── api/             # products, pricing, agents (SSE), simulator, analytics, connections
│   │   ├── db/              # SQLAlchemy models + async session
│   │   ├── integrations/    # BasePricingIntegration + 3 mock HTTP clients
│   │   └── core/            # auth, security, deps, config
│   └── seed_demo.py
├── mock_services/
│   ├── combined/            # Single-port FastAPI app (:9000) with /trendyol /amazon /own_site routers
│   ├── trendyol/            # Standalone :9001
│   ├── amazon/              # Standalone :9002
│   └── own_site/            # Standalone :9003
└── frontend/
    └── src/
        ├── app/
        │   ├── (landing)/   # / landing page
        │   ├── pricing/     # /pricing static page
        │   ├── plan/        # /plan authenticated plan panel
        │   ├── products/    # list + new + [id] detail
        │   ├── logs/        # SSE live terminal
        │   ├── simulator/   # competitor price editor
        │   ├── dashboard/   # analytics + insights
        │   ├── connections/ # platform account management
        │   └── profile/     # user profile
        ├── components/      # AgentReasoningCard, AgentChainTimeline, SalesAssistant,
        │                    # ConfidenceBar, InsightsCard, PriceHistoryChart, FloatingActions
        └── lib/api.ts       # typed API client
```

---

## License

GNU AGPL v3 — see [LICENSE](./LICENSE)
