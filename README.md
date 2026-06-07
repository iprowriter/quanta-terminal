# Quanta Terminal

> AI-powered investment research terminal for emerging compute intelligence stocks.

Quanta Terminal is a production-grade, multi-agent research platform focused on the quantum computing and AI chip sector. It automatically ingests SEC filings, earnings call data, news, and academic research papers — then uses a LangGraph multi-agent workflow to generate structured investment memos on demand.

**Live demo:** [quantaterminal.dev](https://quantaterminal.dev) *(coming soon)*

---

## What it does

Select any of 10 tracked stocks and the platform:

1. **Fetches live data** across 4 sources — SEC EDGAR, financial data, news, and arXiv research papers — via dedicated MCP servers
2. **Runs 5 specialist AI agents in parallel** — SEC, earnings, news, tech, and analyst — each focused on a specific data domain
3. **Synthesises a structured investment memo** including verdict, financial analysis, technology assessment, risk factors, and cited sources
4. **Powers a context-aware research chat** grounded in indexed documents with a LangGraph router that handles memo follow-ups, cross-stock queries, and live data lookups
5. **Monitors for new filings and news spikes** and automatically re-runs agents when material events occur

---

## Tracked stocks

| Ticker | Company | Category |
|--------|---------|----------|
| QUBT | Quantum Computing Inc. | Photonic QPU |
| IONQ | IonQ Inc. | Trapped-ion quantum |
| RGTI | Rigetti Computing | Superconducting quantum |
| QBTS | D-Wave Quantum | Quantum annealing |
| NVDA | NVIDIA Corp. | AI compute |
| SMCI | Super Micro Computer | AI infrastructure |
| MSTR | MicroStrategy | AI + Bitcoin |
| ARQQ | Arqit Quantum | Quantum encryption |
| IBMQ | IBM Quantum | Quantum services |
| INTC | Intel Corp. | AI silicon |

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                   Next.js Frontend                    │
│         (watchlist · memo · chat · alerts)            │
└──────────────────────┬───────────────────────────────┘
                       │ REST + SSE (streaming)
┌──────────────────────▼───────────────────────────────┐
│                   FastAPI Backend                     │
├───────────────────────────────────────────────────────┤
│               LangGraph Agent Pipeline                │
│                                                       │
│   Orchestrator                                        │
│        ↓  (parallel fan-out)                          │
│   ┌──────────┬──────────┬──────────┬───────────┐      │
│   SEC Agent  News Agent  Tech Agent  Analyst Agent    │
│   └──────────┴──────────┴──────────┴───────────┘      │
│        ↓  (join → Earnings Agent → Memo Writer)       │
├───────────────────────────────────────────────────────┤
│                    MCP Servers                        │
│    sec-mcp · finance-mcp · news-mcp · research-mcp    │
├───────────────────────────────────────────────────────┤
│   Pinecone (RAG)  ·  Redis (cache)  ·  Postgres (DB)  │
└───────────────────────────────────────────────────────┘
          │              │               │
     SEC EDGAR      Yahoo Finance    NewsAPI / arXiv
```

---

## Tech stack

### Backend
| Layer | Technology |
|-------|-----------|
| Framework | [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn |
| Agent orchestration | [LangGraph](https://langchain-ai.github.io/langgraph/) |
| LLM | [Google Gemini](https://ai.google.dev/) via `langchain-google-genai` |
| Observability | [LangSmith](https://smith.langchain.com/) |
| MCP servers | [FastMCP](https://github.com/jlowin/fastmcp) |
| MCP ↔ LangChain | [langchain-mcp-adapters](https://github.com/langchain-ai/langchain-mcp-adapters) |
| Vector store | [Pinecone](https://www.pinecone.io/) |
| Cache | Redis via [Upstash](https://upstash.com/) |
| Database | PostgreSQL via [Supabase](https://supabase.com/) |
| Background jobs | Celery + Redis |
| Package manager | [uv](https://docs.astral.sh/uv/) |

### Frontend
| Layer | Technology |
|-------|-----------|
| Framework | [Next.js 14](https://nextjs.org/) (App Router) |
| Language | TypeScript |
| Styling | [Tailwind CSS](https://tailwindcss.com/) + [shadcn/ui](https://ui.shadcn.com/) |
| State | [Zustand](https://zustand-demo.pmnd.rs/) |
| Server state | [TanStack Query](https://tanstack.com/query) |
| Charts | [Recharts](https://recharts.org/) |
| Streaming | Server-Sent Events (SSE) |

### Data sources
| Source | Data | Cost |
|--------|------|------|
| [SEC EDGAR](https://www.sec.gov/developer) | 10-K, 10-Q, 8-K filings | Free |
| [Yahoo Finance](https://finance.yahoo.com/) | Price, fundamentals, earnings | Free |
| [NewsAPI](https://newsapi.org/) | News articles | Free tier |
| [arXiv](https://arxiv.org/) | Research papers | Free |

---

## Project structure

```
quanta-terminal/
├── backend/
│   ├── agents/                  # LangGraph agent definitions
│   │   ├── graph.py             # Main pipeline graph
│   │   ├── orchestrator.py      # Routing + fan-out logic
│   │   ├── sec_agent.py
│   │   ├── news_agent.py
│   │   ├── tech_agent.py
│   │   ├── analyst_agent.py
│   │   ├── earnings_agent.py
│   │   └── memo_writer.py
│   ├── mcp_servers/             # FastMCP tool servers
│   │   ├── sec_mcp.py           # SEC EDGAR tools
│   │   ├── finance_mcp.py       # yfinance tools
│   │   ├── news_mcp.py          # NewsAPI + RSS tools
│   │   └── research_mcp.py      # arXiv tools
│   ├── api/                     # FastAPI routes
│   │   ├── main.py
│   │   ├── routes/
│   │   └── schemas/
│   ├── core/
│   │   └── config.py            # Settings via pydantic-settings
│   ├── pyproject.toml           # Dependencies managed by uv
│   └── test_mcp_servers.py      # Phase 1 integration tests
├── frontend/                    # Next.js app (Phase 4)
├── .env.example                 # Environment variable template — safe to commit
├── .env                         # Your real keys — never commit this
├── .gitignore
└── README.md
```

---

## Getting started

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Node.js 20+ *(frontend only, Phase 4)*
- Redis — local or [Upstash](https://upstash.com/) free tier
- Accounts for: [Google AI Studio](https://aistudio.google.com), [Pinecone](https://pinecone.io), [Supabase](https://supabase.com), [LangSmith](https://smith.langchain.com)

### 1. Clone and configure

```bash
git clone https://github.com/yourusername/quanta-terminal.git
cd quanta-terminal

cp .env.example .env
# Edit .env and fill in your API keys
```

### 2. Install backend dependencies

```bash
cd backend
uv sync
```

This creates a `.venv`, resolves the lockfile, and installs all dependencies. To activate manually in a new terminal:

```bash
# Option A — prefix any command with uv run (recommended)
uv run python script.py

# Option B — activate the venv directly
source .venv/bin/activate
```

### 3. Run Phase 1 integration tests

Verifies all MCP servers can reach their data sources and return real data for QUBT:

```bash
cd backend
uv run python test_mcp_servers.py
```

Expected output:
```
✓  get_company_info       → Quantum Computing Inc. (CIK 1862463)
✓  search_filings (10-K)  → 2 filings found, latest: 2025-03-15
✓  get_company_facts      → cash=$67,000,000
✓  get_stock_info         → $8.42 | market cap $1,200,000,000
✓  get_financials         → revenue_ttm=$3,800,000
✓  search_papers          → 5 papers found
✓  get_papers_for_ticker  → 8 papers for QUBT
```

### 4. Start the backend *(Phase 2+)*

```bash
cd backend
uv run uvicorn api.main:app --reload --port 8000
```

### 5. Start the frontend *(Phase 4)*

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

---

## Environment variables

Copy `.env.example` to `.env` and fill in the values.

| Variable | Required for | Where to get it |
|----------|-------------|-----------------|
| `GOOGLE_API_KEY` | Phase 2+ | [aistudio.google.com](https://aistudio.google.com) |
| `LANGSMITH_API_KEY` | Phase 2+ | [smith.langchain.com](https://smith.langchain.com) |
| `PINECONE_API_KEY` | Phase 2+ | [pinecone.io](https://pinecone.io) |
| `NEWS_API_KEY` | Phase 1 | [newsapi.org](https://newsapi.org) — free tier |
| `SUPABASE_URL` + `SUPABASE_KEY` | Phase 3+ | [supabase.com](https://supabase.com) |
| `REDIS_URL` | Phase 3+ | [upstash.com](https://upstash.com) free tier |

> ⚠️ **Never commit `.env`** — it is listed in `.gitignore`. Only `.env.example` (with placeholder values) belongs in version control.

---

## Development workflow

```bash
# Add a runtime dependency
uv add package-name

# Add a dev-only dependency
uv add --dev package-name

# Lint
uv run ruff check .

# Type check
uv run pyright

# Run tests
uv run pytest
```

---

## Build phases

| Phase | Status | Scope |
|-------|--------|-------|
| **1 — MCP servers** | ✅ Complete | Data ingestion: SEC, finance, news, research |
| **2 — Agent pipeline** | 🔄 In progress | LangGraph multi-agent memo generation |
| **3 — Caching + auth** | ⏳ Planned | Redis cache, JWT auth, Supabase integration |
| **4 — Frontend** | ⏳ Planned | Next.js dashboard, streaming UI, alerts |

---

## Roadmap

- [ ] Earnings transcript ingestion
- [ ] Cross-stock comparison agent
- [ ] Automated alerts (Celery + SEC EDGAR polling)
- [ ] Shareable memo URLs with public view
- [ ] Token cost tracking per memo run
- [ ] Mobile-responsive frontend

---

## License

MIT
