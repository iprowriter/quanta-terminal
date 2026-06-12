"""
Quanta Terminal — FastAPI application entry point.

Startup sequence (lifespan):
  1. Sentry initialised (if DSN configured)
  2. All 5 specialist agent MCP subprocesses initialised in parallel
  3. LangGraph pipeline graph compiled
  4. Redis connection verified (ping)
  5. App begins accepting requests

Run with:
    uv run uvicorn api.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from agents.graph import initialize as init_pipeline
from api.routes import auth, memo, stocks, chat
from core import redis as cache
from core.config import settings


# ---------------------------------------------------------------------------
# Sentry
# ---------------------------------------------------------------------------

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.app_env,
        integrations=[
            StarletteIntegration(transaction_style="url"),
            FastApiIntegration(transaction_style="url"),
        ],
        # Capture 100% of transactions in dev, 10% in production
        traces_sample_rate=1.0 if settings.app_env == "development" else 0.1,
        send_default_pii=False,   # don't send emails/IPs to Sentry
    )


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("⚡ Quanta Terminal: initialising agent pipeline…")
    await init_pipeline()
    print("✓  All agents ready.")

    redis_ok = await cache.ping()
    print(f"✓  Redis {'connected' if redis_ok else 'UNAVAILABLE — caching disabled'}.")

    yield

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
# Global exception handler — captures unhandled errors in Sentry
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    sentry_sdk.capture_exception(exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred. Our team has been notified."},
    )


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    settings.frontend_url,   # set FRONTEND_URL in Render to your Vercel domain
]

if settings.app_env == "development":
    _CORS_ORIGINS.append("*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
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
    redis_ok = await cache.ping()
    return {
        "status":  "ok",
        "version": "0.1.0",
        "redis":   "connected" if redis_ok else "unavailable",
        "sentry":  "enabled" if settings.sentry_dsn else "disabled",
    }


@app.get("/api/tickers", tags=["meta"], summary="List tracked tickers")
async def get_tickers():
    return {"tickers": settings.tracked_tickers}
