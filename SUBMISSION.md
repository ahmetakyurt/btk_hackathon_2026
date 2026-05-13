# OptiPrice AI — Hackathon Başvuru Dokümanı

> **Yarışma:** BTK Akademi × Google × Girvak — Shackathon'26
> **Takım:** ahmetakyurt
> **Son Teslim:** 19 Mayıs 2026 23:59

---

## Proje Özeti (Tr)

**OptiPrice AI**, e-ticaret satıcılarının aynı ürünü birden fazla platformda (Trendyol, Amazon, kendi sitesi) otonom olarak yönetmesini sağlayan **Agentic SaaS** kontrol panelidir.

Satıcı ürünü **bir kez** tanımlar; Google Gemini destekli yapay zeka ajanları:
1. Her platforma özel SEO uyumlu başlık ve açıklamalarla **otomatik listeler**
2. Rakip fiyatlarını **gerçek zamanlı izler**
3. Komisyon + kargo + maliyet kısıtları altında **otonom fiyat günceller**
4. Tüm kararları **canlı log dashboard'unda** şeffaflaştırır

Her platformun farklı ekonomik mantığına göre (Trendyol buybox odaklı, Amazon lojistik dengeli, OwnSite kâr maksimizasyonu) üç ayrı ajan stratejisiyle fiyatlama yapar.

---

## Teknik Detaylar

| Katman | Teknoloji |
|--------|-----------|
| **Frontend** | Next.js 16 (App Router), TypeScript, Tailwind CSS, Shadcn UI, Recharts |
| **Backend** | FastAPI (Python 3.12), SQLAlchemy 2.0 (async), Pydantic v2 |
| **Veritabanı** | Supabase Postgres (asyncpg), Row Level Security |
| **AI / Agent** | Google Gemini 2.5 Flash — Function Calling, Structured Outputs |
| **Auth** | NextAuth v5 (JWT), bcrypt, email/şifre + şifre sıfırlama (Resend) |
| **Realtime** | SSE (Server-Sent Events) — canlı agent log akışı |
| **Mock Servisler** | FastAPI tabanlı 3 mock platform (Trendyol, Amazon, OwnSite) |
| **Deploy** | Railway (backend + mock servisler), Vercel (frontend) |

### Mimari

```
Next.js 16 → FastAPI → Gemini 2.5 Flash (ListingAgent + PricingAgent)
                    → Mock Platform Services (Trendyol / Amazon / OwnSite)
                    → Supabase Postgres
                    → SSE → Frontend Live Logs
```

### Ajan Mimarisi

- **ListingAgent:** Gemini Structured Output → platform bazlı `{title, description, keywords[]}` üretir. Her platformun SEO/ton farkını dikkate alır.
- **PricingAgent:** Function Calling ile max 6 turlu otonom karar zinciri. 4 tool: `get_competitor_prices`, `calculate_floor_price`, `update_platform_price`, `log_decision`.
- **CompetitorWatcher:** Async background loop, 5sn polling, ≥0.50 TL fiyat değişiminde PricingAgent'i tetikler.

### Veritabanı Şeması

6 tablo: `users`, `products`, `platforms`, `product_platform_status`, `pricing_agent_logs`, `platform_connections`, `password_reset_tokens`

---

## Kod Linki

<!-- TODO: GitHub repo public yapıldıktan sonra linki buraya ekle -->
**GitHub:** [Link eklenecek]

---

## Demo Video

<!-- TODO: Video çekildikten sonra linki buraya ekle -->
**Video:** [Link eklenecek]

---

## Takım Bilgisi

- **Ad Soyad:** Ahmet Akyurt
- **Email:** [email eklenecek]
- **GitHub:** ahmetakyurt

---

## Çalıştırma (Yerel)

```bash
# Gereksinimler: Python 3.12, Node.js 20+, pnpm

# Mock servisler (combined)
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

# http://localhost:3000 — frontend
# http://localhost:8000/docs — backend Swagger
```

### Docker Compose

```bash
docker compose build --no-cache && docker compose up
# http://localhost:3000
```

### Environment Variables

Backend `.env`:
```
GEMINI_API_KEY=...
DATABASE_URL=postgresql+asyncpg://...
NEXTAUTH_SECRET=...
RESEND_API_KEY=...
```

Frontend `.env.local`:
```
AUTH_SECRET=...
BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

---

## Lisans

GNU AGPL v3 — Bkz. [LICENSE](./LICENSE)
