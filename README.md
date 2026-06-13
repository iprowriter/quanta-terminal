# Quanta Terminal

> AI-powered investment research terminal for emerging compute stocks.

**Live:** [quanta-terminal.vercel.app](https://quanta-terminal.vercel.app)

Quanta Terminal is a production-grade multi-agent research platform focused on the quantum computing and AI chip sector. Select any tracked stock and the system automatically ingests SEC filings, earnings data, news, and academic research papers — then runs five specialist AI agents in parallel to generate a structured investment memo, streamed live to your browser.

---

## What it does

1. **Live stock watchlist** — prices, % change, market cap and volume for 10 tracked tickers, auto-refreshed every 60 seconds
2. **Multi-agent memo generation** — five specialist agents run in parallel, each with their own MCP-connected data source; results are streamed to the UI via Server-Sent Events as each agent completes
3. **Research chat** — after a memo is generated, a context-aware chat sidebar lets you interrogate any of the five agents independently on that stock
4. **Memo persistence** — generated memos are cached in Redis and stored in Supabase so repeat views are instant
5. **Auth** — passwordless magic-link login via Supabase; memo generation and chat require authentication

---

## Agent pipeline

```
User requests memo for TICKER
         │
         ▼
┌─────────────────────────────────────────────────────┐
│              LangGraph Pipeline (graph.py)           │
│                                                     │
│   asyncio.gather — 5 agents run in parallel:        │
│                                                     │
│   ┌───────────┐  ┌───────────┐  ┌───────────┐      │
│   │ SEC Agent │  │  Analyst  │  │  Earnings │      │
│   │ sec_mcp   │  │ finance   │  │  finance  │      │
│   │ (EDGAR)   │  │  _mcp     │  │   _mcp    │      │
│   └───────────┘  └───────────┘  └───────────┘      │
│   ┌───────────┐  ┌───────────┐                     │
│   │   News    │  │ Research  │                     │
│   │  news_mcp │  │research   │                     │
│   │(NewsAPI)  │  │  _mcp     │                     │
│   └───────────┘  └───────────┘                     │
│         │                                           │
│         ▼  (all 5 complete → join)                  │
│   ┌─────────────┐                                   │
│   │ Memo Writer │  (Gemini synthesis)               │
│   └─────────────┘                                   │
└─────────────────────────────────────────────────────┘
         │  SSE stream (agent_complete events → memo_complete)
         ▼
    Next.js frontend
```

Each agent is a self-contained LangGraph `StateGraph` with:
- Its own MCP subprocess for data access
- `MemorySaver` checkpointer for per-thread chat history
- Tool-calling loop with a 6-call guard against infinite loops

---

## MCP servers

| Server | Tools | Data source |
|--------|-------|-------------|
| `sec_mcp.py` | `get_company_info`, `search_filings`, `get_filing_text`, `get_company_facts`, `get_recent_8k_events` | SEC EDGAR (free) |
| `finance_mcp.py` | `get_stock_info`, `get_financials`, `get_analyst_recommendations`, `get_price_history`, `get_earnings` | Yahoo Finance via yfinance (free) |
| `news_mcp.py` | `search_news`, `detect_news_spike`, `get_sector_news` | NewsAPI |
| `research_mcp.py` | `search_papers`, `get_papers_for_ticker`, `get_paper_detail`, `get_sector_research_pulse` | arXiv (free) |

MCP servers run as stdio subprocesses managed by `MultiServerMCPClient` from `langchain-mcp-adapters`. They are started once at FastAPI lifespan and kept alive for the process lifetime.

---

## Tracked stocks

| Ticker | Company | Sector |
|--------|---------|--------|
| QUBT | Quantum Computing Inc. | Photonic QPU |
| IONQ | IonQ Inc. | Trapped-ion quantum |
| RGTI | Rigetti Computing | Superconducting quantum |
| QBTS | D-Wave Quantum | Quantum annealing |
| NVDA | NVIDIA Corp. | AI compute |
| SMCI | Super Micro Computer | AI infrastructure |
| MSTR | MicroStrategy | Bitcoin / AI |
| ARQQ | Arqit Quantum | Quantum encryption |
| IBM | IBM | Quantum services |
| INTC | Intel Corp. | AI silicon |

---

## Tech stack

### Backend

| Layer | Technology |
|-------|-----------|
| Framework | [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn |
| Agent orchestration | [LangGraph](https://langchain-ai.github.io/langgraph/) |
| LLM | [Google Gemini](https://ai.google.dev/) (`gemini-2.5-flash-lite`) via `langchain-google-genai` |
| LLM tracing | [LangSmith](https://smith.langchain.com/) |
| MCP servers | [FastMCP](https://github.com/jlowin/fastmcp) |
| MCP ↔ LangChain | [langchain-mcp-adapters](https://github.com/langchain-ai/langchain-mcp-adapters) |
| Auth / DB | [Supabase](https://supabase.com/) — PostgreSQL + magic-link auth + ES256 JWT verification |
| Cache | Redis via [Upstash](https://upstash.com/) — cache-aside with Redis rate limiting |
| Error tracking | [Sentry](https://sentry.io/) |
| Package manager | [uv](https://docs.astral.sh/uv/) |

### Frontend

| Layer | Technology |
|-------|-----------|
| Framework | [Next.js 14](https://nextjs.org/) App Router |
| Language | TypeScript |
| Styling | Inline CSS (no Tailwind) — dark terminal aesthetic |
| Auth | Supabase JS client with magic-link OTP |
| Streaming | Server-Sent Events via `fetch` + `ReadableStream` |
| Error tracking | [Sentry](https://sentry.io/) (`@sentry/nextjs`) |

### Data sources

| Source | Used for | Cost |
|--------|----------|------|
| [SEC EDGAR](https://www.sec.gov/developer) | 10-K, 10-Q, 8-K filings | Free |
| [Yahoo Finance](https://finance.yahoo.com/) | Price, fundamentals, earnings, analyst ratings | Free (yfinance) |
| [NewsAPI](https://newsapi.org/) | News articles and headlines | Free tier |
| [arXiv](https://arxiv.org/) | Academic research papers | Free |

---

## Deployment

| Service | Platform | Notes |
|---------|----------|-------|
| Frontend | [Vercel](https://vercel.com) | Root directory: `frontend`; calls backend via `NEXT_PUBLIC_API_URL` |
| Backend | [Railway](https://railway.app) | Root directory: `/backend`; build: `pip install .`; start: `uvicorn api.main:app --host 0.0.0.0 --port $PORT --workers 1` |
| Database | [Supabase](https://supabase.com) | PostgreSQL with Row Level Security; memos table + `latest_memos` view |
| Cache | [Upstash](https://upstash.com) | Redis with TLS (`rediss://`); 60s stock TTL, 24h memo TTL |

> The frontend calls the Railway backend directly (not proxied through Vercel) because Vercel's edge network blocks outbound requests to Railway IPs. CORS is configured on the backend to allow the Vercel origin.

---

## Project structure

```
quanta-terminal/
├── backend/
│   ├── agents/
│   │   ├── graph.py             # Main LangGraph pipeline + SSE streaming
│   │   ├── analyst_agent.py     # Valuation, price targets, financials
│   │   ├── earnings_agent.py    # EPS history, beat/miss streaks, guidance
│   │   ├── sec_agent.py         # SEC filings, cash runway, dilution risk
│   │   ├── news_agent.py        # News sentiment, coverage spikes
│   │   ├── research_agent.py    # arXiv papers, technology positioning
│   │   └── memo_writer.py       # Final memo synthesis (Gemini)
│   ├── mcp_servers/
│   │   ├── sec_mcp.py           # SEC EDGAR tools (FastMCP)
│   │   ├── finance_mcp.py       # yfinance tools
│   │   ├── news_mcp.py          # NewsAPI tools
│   │   └── research_mcp.py      # arXiv tools
│   ├── api/
│   │   ├── main.py              # FastAPI app, lifespan, CORS, Sentry
│   │   ├── routes/
│   │   │   ├── stocks.py        # GET /api/v1/stocks — live prices (Redis cached)
│   │   │   ├── memo.py          # POST /api/v1/memo/{ticker}/generate — SSE stream
│   │   │   │                    # GET  /api/v1/memo/{ticker} — fetch cached memo
│   │   │   ├── chat.py          # POST /api/v1/chat — agent chat (auth required)
│   │   │   └── auth.py          # GET  /api/v1/auth/me — JWT identity
│   │   ├── schemas/
│   │   │   └── memo.py          # Pydantic models for all routes
│   │   └── dependencies.py      # get_current_user, CurrentUser, OptionalCurrentUser
│   ├── core/
│   │   ├── config.py            # Settings via pydantic-settings (.env)
│   │   ├── security.py          # ES256/HS256 JWT verification, JWKS cache
│   │   ├── database.py          # Supabase client — save_memo, get_latest_memo
│   │   ├── redis.py             # Async Redis client — get_json, set_json
│   │   └── rate_limit.py        # Redis-backed rate limiting (memo: 5/day, chat: 60/hr)
│   ├── prompts/
│   │   └── system_prompts.py    # System prompts for all 5 agents + memo writer
│   ├── supabase/
│   │   └── migrations/
│   │       └── 001_create_memos.sql
│   ├── pyproject.toml           # uv-managed dependencies
│   ├── railway.toml             # Railway deployment config
│   └── test_mcp_servers.py      # Phase 1 integration tests
├── frontend/
│   ├── app/
│   │   ├── layout.tsx           # Root layout, AuthProvider, Header
│   │   ├── page.tsx             # Watchlist (home)
│   │   ├── memo/[ticker]/
│   │   │   └── page.tsx         # Memo + chat page
│   │   └── auth/callback/
│   │       └── route.ts         # Magic-link exchange handler
│   ├── components/
│   │   ├── ui/
│   │   │   ├── Header.tsx       # Sticky header, user menu, sign in/out
│   │   │   └── Skeleton.tsx     # Shimmer loading skeletons
│   │   ├── watchlist/
│   │   │   └── WatchlistTable.tsx  # Live price table, 60s auto-refresh
│   │   └── memo/
│   │       ├── MemoViewer.tsx   # SSE streaming, markdown render
│   │       ├── AgentProgress.tsx   # 6-step progress indicator
│   │       └── ChatSidebar.tsx  # Agent selector + typewriter chat
│   ├── hooks/
│   │   ├── useAuth.tsx          # Supabase auth context
│   │   └── useTypewriter.ts     # Character-by-character text animation
│   ├── lib/
│   │   ├── api.ts               # fetchStocks, fetchMemo, streamMemo, sendChat
│   │   └── theme.ts             # Design tokens (dark terminal palette)
│   ├── next.config.ts           # Sentry config
│   ├── sentry.client.config.ts
│   └── sentry.server.config.ts
├── .env.example                 # Template — safe to commit
└── README.md
```

---

## Local development

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Node.js 20+
- A Redis instance — local or [Upstash](https://upstash.com/) free tier
- Accounts for: [Google AI Studio](https://aistudio.google.com), [Supabase](https://supabase.com), [LangSmith](https://smith.langchain.com), [NewsAPI](https://newsapi.org)

### 1. Clone and configure

```bash
git clone https://github.com/yourusername/quanta-terminal.git
cd quanta-terminal

cp .env.example .env
# Fill in your API keys in .env
```

### 2. Backend

```bash
cd backend
uv sync                               # installs deps into .venv
uv run uvicorn api.main:app --reload --port 8000
```

API docs available at `http://localhost:8000/docs`.

### 3. Frontend

```bash
cd frontend
cp .env.local.example .env.local      # fill in Supabase keys
npm install
npm run dev
# → http://localhost:3000
```

### 4. Run MCP integration tests

Verifies all four MCP servers can reach their data sources:

```bash
cd backend
uv run python test_mcp_servers.py
```

---

## Environment variables

### Backend (`.env` in project root or Railway Variables)

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | ✅ | Gemini API key from [aistudio.google.com](https://aistudio.google.com) |
| `NEWS_API_KEY` | ✅ | [newsapi.org](https://newsapi.org) free tier |
| `SUPABASE_URL` | ✅ | Supabase project URL |
| `SUPABASE_ANON_KEY` | ✅ | Supabase anon/public key |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ | Supabase service role key (for writes) |
| `SUPABASE_JWT_SECRET` | ✅ | For HS256 JWT fallback verification |
| `REDIS_URL` | ✅ | `rediss://...` for Upstash, `redis://localhost:6379/0` for local |
| `FRONTEND_URL` | ✅ | Vercel URL for CORS (`https://quanta-terminal.vercel.app`) |
| `LANGSMITH_API_KEY` | Optional | LangSmith tracing |
| `LANGCHAIN_TRACING_V2` | Optional | Set `true` to enable LangSmith |
| `SENTRY_DSN` | Optional | Backend error tracking |
| `APP_ENV` | Optional | `development` or `production` (default: `development`) |
| `LLM_PROVIDER` | Optional | `gemini` or `ollama` (default: `gemini`) |
| `MEMO_WRITER_PROVIDER` | Optional | `gemini` or `ollama` (default: `gemini`) |
| `GEMINI_MODEL` | Optional | Model name (default: `gemini-2.5-flash-lite`) |

### Frontend (`.env.local` or Vercel Environment Variables)

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_SUPABASE_URL` | ✅ | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | ✅ | Supabase anon key |
| `NEXT_PUBLIC_API_URL` | ✅ | Railway backend URL + `/api/v1` (e.g. `https://your-app.up.railway.app/api/v1`) |
| `NEXT_PUBLIC_SENTRY_DSN` | Optional | Frontend error tracking |
| `SENTRY_AUTH_TOKEN` | Optional | Source map upload to Sentry |

> ⚠️ Never commit `.env` or `.env.local`. Only `.env.example` belongs in version control.

---

## Key design decisions

**Why MCP for data access?**
Each data source runs as an isolated subprocess with a defined tool schema. Agents call tools via the MCP protocol — this means tools can be swapped, versioned, or replaced without touching agent logic.

**Why LangGraph?**
The pipeline has a fan-out (5 agents in parallel) followed by a join (memo writer receives all 5 outputs). LangGraph's `StateGraph` handles this cleanly. `MemorySaver` gives each chat thread persistent conversation history without a database.

**Why inline CSS instead of Tailwind?**
Terminal aesthetic with tight spacing and custom glow effects — inline CSS gives precise control without a build step configuration overhead.

**Why call Railway directly from the browser?**
Vercel's edge network blocks outbound connections to Railway IPs (`DNS_HOSTNAME_RESOLVED_PRIVATE`). Rather than adding a proxy layer, the frontend calls the Railway URL directly using `NEXT_PUBLIC_API_URL`. CORS on the backend allows the Vercel origin.

**Rate limiting strategy**
Redis atomic `INCR + EXPIRE` pattern. Fails open if Redis is unavailable so users aren't blocked by infrastructure issues. Limits: 5 memo generations per user per day, 60 chat messages per user per hour.

---

## Supabase setup

Run the migration to create the memos table:

```sql
-- supabase/migrations/001_create_memos.sql
-- (run via Supabase SQL editor or CLI)
```

The migration creates:
- `memos` table with RLS (public reads, service-role-only writes)
- Indexes on `(ticker, created_at desc)` for fast lookups
- `latest_memos` view that returns one memo per ticker

---

## Roadmap

- [ ] Earnings transcript ingestion (SEC 8-K earnings call text)
- [ ] Cross-stock comparison agent (side-by-side memo diff)
- [ ] Automated re-generation on new 8-K filings (Railway cron job)
- [ ] Shareable memo URLs with public read view
- [ ] Token cost tracking per memo run (LangSmith callbacks)
- [ ] Export memo as PDF

---

## License

Copyright (c) 2026 Martin Oputa. All rights reserved.

This software and its source code are proprietary and confidential. 
No part of this software may be cloned, copied, reproduced, distributed, 
or transmitted in any form or by any means without the prior written 
permission of the copyright owner.

