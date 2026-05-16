# OptiPrice AI — Hackathon Başvuru Dokümanı

> **Yarışma:** BTK Akademi × Google × GİRVAK — Hackathon'26
> **Takım:** ahmetakyurt
> **Son Teslim:** 19 Mayıs 2026 23:59

---

## Proje Özeti

**OptiPrice AI**, e-ticaret satıcılarının aynı ürünü birden fazla platformda (Trendyol, Amazon, kendi sitesi) otonom olarak yönetmesini sağlayan **Agentic SaaS** kontrol panelidir.

Satıcı ürünü **bir kez** tanımlar; Google Gemini 2.5 Flash destekli yapay zeka ajanları:

1. Her platforma özel SEO uyumlu başlık ve açıklamalarla **otomatik listeler**
2. Rakip fiyatlarını **gerçek zamanlı izler** (5 sn polling)
3. Komisyon + kargo + maliyet kısıtları altında **otonom fiyat günceller**
4. Düşük güvende insan onayı bekler (**Human-in-the-Loop**)
5. Tüm kararları **canlı log dashboard'unda** şeffaflaştırır

Her platformun farklı ekonomik mantığına göre üç ayrı ajan stratejisiyle fiyatlama yapar: Trendyol buybox odaklı, Amazon medyan dengeli, OwnSite kâr maksimizasyonu.

---

## Öne Çıkan Özellikler

| Özellik | Açıklama |
|---------|----------|
| **Multi-Platform Listing** | ListingAgent: Gemini Structured Output ile 3 platforma paralel, platforma özel AI içerik |
| **Otonom Fiyatlandırma** | PricingAgent: Function Calling loop, max 6 tur, 4 tool, outlier detection, buybox-aware |
| **Smart Pricing Strategies** | Trendyol: buybox (rakip −0.50 ₺), Amazon: medyan dengesi, OwnSite: kâr maks (%5 kademeli) |
| **Human-in-the-Loop** | Güven skoru <75'te PENDING_APPROVAL → Onayla/Reddet flow'u |
| **Proaktif AI Öneriler** | Dashboard'da Gemini destekli 3-5 Türkçe aksiyon önerisi (pricing/stock/listing/general) |
| **Stok Tabanlı Fiyatlandırma** | Stok ≤10 → otomatik profit_max stratejisi, 1 saat cooldown |
| **Canlı SSE Log Akışı** | Terminal görünümlü panel, per-user queue, sıralama toggle, pending approval inline |
| **Agent Reasoning Card** | Her platform kartında expandable Gemini gerekçesi + tool çağrıları + ConfidenceBar |
| **Agent Zinciri Timeline** | Ürün bazlı tüm ajan aktivitesi kronolojik zincir olarak görselleştirilmiş |
| **Satış Asistanı** | Ürün başına bağlamsal Gemini chat paneli (ürün + loglar bağlam) |
| **Competitor Simulator** | Jüri demo paneli: rakip fiyatı değiştir → ajan 5 sn içinde tepki verir |
| **Dashboard & Analytics** | Platform bazlı kâr, buybox oranı, fiyat geçmişi LineChart (Recharts) |
| **Platform Hesap Bağlantısı** | Gerçek API akışını taklit eden credential yönetimi, test + bağlantı kes |
| **Mobil Responsive** | Hamburger menü, sidebar overlay, tablo yatay scroll, buton sarma |
| **Auth & Multi-Tenant** | NextAuth v5 JWT, bcrypt, şifre sıfırlama (Resend email), user-izole data |

---

## Teknik Detaylar

| Katman | Teknoloji |
|--------|-----------|
| **Frontend** | Next.js 16 (App Router), TypeScript, Tailwind CSS, Shadcn UI, Recharts |
| **Backend** | FastAPI (Python 3.12), SQLAlchemy 2.0 (async), Pydantic v2, asyncpg |
| **Veritabanı** | Supabase Postgres, Row Level Security |
| **AI / Agent** | Google Gemini 2.5 Flash — Function Calling, Structured Outputs |
| **Auth** | NextAuth v5 (JWT), bcrypt, şifre sıfırlama (Resend) |
| **Realtime** | SSE (Server-Sent Events) — canlı agent log akışı, per-user queue |
| **Mock Servisler** | FastAPI tabanlı 3 mock platform (Trendyol :9001, Amazon :9002, OwnSite :9003) |
| **Deploy** | Railway (backend + mock servisler), Vercel (frontend) |

### Mimari

```
Next.js 16 → FastAPI → Gemini 2.5 Flash (ListingAgent + PricingAgent + SalesAssistant + InsightsAgent)
                     → Mock Platform Services (Trendyol / Amazon / OwnSite)
                     → Supabase Postgres
                     → SSE → Frontend Live Logs
```

### Ajan Mimarisi

- **ListingAgent:** Gemini Structured Output → platform bazlı `{title, description, keywords[]}`. Trendyol=SEO/keyword, Amazon=bullet/teknik, OwnSite=marka hikayesi. asyncio.gather ile 3 platforma paralel.
- **PricingAgent:** Function Calling loop, max 6 tur, 4 tool (`get_competitor_prices`, `calculate_floor_price`, `update_platform_price`, `log_decision`). Outlier detection, buybox-aware, confidence scoring, HITL flow.
- **CompetitorWatcher:** Async background loop, 5 sn polling. ≥0.50 ₺ fiyat değişimi veya stok ≤10 tetikleyici.
- **SalesAssistant:** Ürün + platform durumu + son 10 log bağlam → Gemini Türkçe cevap.
- **InsightsAgent:** Son 24s log + buybox/stok verileri → 3-5 öncelikli aksiyon önerisi.

### Veritabanı

7 tablo: `users`, `products`, `platforms`, `product_platform_status`, `pricing_agent_logs`, `platform_connections`, `password_reset_tokens`

---

## Çalıştırma (Yerel)

```bash
# Gereksinimler: Python 3.12, Node.js 20+, pnpm

# Mock servisler (combined — tek port)
cd mock_services/combined
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt
.venv/Scripts/uvicorn main:app --port 9000

# Backend
cd backend
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt
.venv/Scripts/uvicorn app.main:app --port 8000

# Frontend
cd frontend
pnpm install && pnpm dev
# http://localhost:3000
```

**Docker Compose:**
```bash
docker compose build --no-cache && docker compose up
```

**Environment Variables — Backend `.env`:**
```
GEMINI_API_KEY=...
DATABASE_URL=postgresql+asyncpg://...
NEXTAUTH_SECRET=...
RESEND_API_KEY=...
RESEND_FROM_EMAIL=noreply@...
APP_PUBLIC_URL=http://localhost:3000
MOCK_TRENDYOL_URL=http://localhost:9000/trendyol
MOCK_AMAZON_URL=http://localhost:9000/amazon
MOCK_OWN_SITE_URL=http://localhost:9000/own_site
```

**Frontend `.env.local`:**
```
AUTH_SECRET=...
BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

---

## Kod & Demo

**GitHub:** [Link eklenecek — repo public yapıldıktan sonra]

**Demo Video:** [Link eklenecek]

**Canlı Demo:** Railway + Vercel deploy'u mevcut (URL'ler eklenecek)

---

## Takım Bilgisi

- **Ad Soyad:** Ahmet Akyurt
- **Email:** ahmetakyurt2021@gmail.com
- **GitHub:** ahmetakyurt

---

## Lisans

GNU AGPL v3 — Bkz. [LICENSE](./LICENSE)
