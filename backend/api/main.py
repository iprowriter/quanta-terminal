"""
Quanta Terminal — FastAPI application entry point.

Startup sequence (lifespan):
  1. All 5 specialist agent MCP subprocesses initialised in parallel
  2. LangGraph pipeline graph compiled
  3. Redis connection verified (ping)
  4. App begins accepting requests

Run with:
    uv run uvicorn api.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agents.graph import initialize as init_pipeline
from api.routes import auth, memo, stocks, chat
from core import redis as cache
from core.config import settings


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialise all agents and connections at startup so the first request
    isn't slow. All 5 MCP subprocesses boot concurrently (~5-10 s).
    """
    print("⚡ Quanta Terminal: initialising agent pipeline…")
    await init_pipeline()
    print("✓  All agents ready.")

    redis_ok = await cache.ping()
    print(f"✓  Redis {'connected' if redis_ok else 'UNAVAILABLE — caching disabled'}.")

    yield

    # Graceful shutdown
    await cache.close()
    print("Quanta Terminal: shutting down.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Quanta Terminal API",
    description="AI-powered investment research for emerging compute intelligence stocks.",
    version="0.1.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

_CORS_ORIGINS = [
    "http://localhost:3000",      # Next.js dev server
    "http://localhost:3001",
    "https://quantaterminal.dev", # Production frontend (Phase 4)
]

if settings.app_env == "development":
    _CORS_ORIGINS.append("*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],   # needed for SSE headers
)


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(stocks.router, prefix="/api/v1")
app.include_router(memo.router,   prefix="/api/v1")
app.include_router(chat.router,   prefix="/api/v1")
app.include_router(auth.router,   prefix="/api/v1")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["meta"], summary="Health check")
async def health():
    """Returns 200 when the server is up and agents are initialised."""
    redis_ok = await cache.ping()
    return {
        "status":  "ok",
        "version": "0.1.0",
        "redis":   "connected" if redis_ok else "unavailable",
    }


@app.get("/api/tickers", tags=["meta"], summary="List tracked tickers")
async def get_tickers():
    """Returns the list of tickers this instance is configured to track."""
    return {"tickers": settings.tracked_tickers}
