# OptiPrice AI

> Multi-channel dynamic pricing & integration agent for e-commerce sellers.
> BTK Akademi × Google × Girvak — **Shackathon'26** submission.

OptiPrice AI is a B2B/SaaS control panel that lets sellers define a product **once** and autonomously:
1. **Lists** it across Trendyol, Amazon, and the seller's own storefront with platform-tailored AI-generated copy,
2. **Watches** competitor prices in real time,
3. **Re-prices** under cost / commission / shipping constraints via a Gemini-powered agentic loop,
4. **Streams** every decision to a live transparency dashboard.

See **[CLAUDE.md](./CLAUDE.md)** for the full project constitution: vision, architecture, schema, agent design, roadmap, and code rules.

---

## Repository Layout

```
bkt_hackathon_2026/
├── CLAUDE.md             # project constitution (read first)
├── backend/              # FastAPI core API + agents
├── mock_services/        # 3 standalone FastAPI apps simulating platforms
│   ├── trendyol/         # :9001
│   ├── amazon/           # :9002
│   └── own_site/         # :9003
└── frontend/             # Next.js dashboard (App Router)
```

---

## Quickstart (development)

### Prerequisites
- Python 3.11+ (tested on 3.14)
- Node.js 20+
- [uv](https://docs.astral.sh/uv/) — Python package manager
- [pnpm](https://pnpm.io/) — Node package manager
- A Gemini API key

### 1. Clone & configure
```bash
git clone <repo-url> optiprice
cd optiprice
copy .env.example .env       # then edit .env and add GEMINI_API_KEY
```

### 2. Backend
```bash
cd backend
uv sync                       # install deps + create .venv
uv run alembic upgrade head   # apply migrations (creates optiprice.db)
uv run uvicorn app.main:app --reload --port 8000
```

### 3. Mock platform services
Each runs as its own FastAPI app:
```bash
# in 3 separate terminals
cd mock_services/trendyol && uv run uvicorn main:app --port 9001 --reload
cd mock_services/amazon   && uv run uvicorn main:app --port 9002 --reload
cd mock_services/own_site && uv run uvicorn main:app --port 9003 --reload
```

### 4. Frontend
```bash
cd frontend
pnpm install
pnpm dev                      # http://localhost:3000
```

---

## Status

Day 1 / 10 — foundation in progress. See [CLAUDE.md §4](./CLAUDE.md#4-step-by-step-implementation-roadmap) for the daily roadmap.
