"""
Stocks route
GET /api/v1/stocks  →  current quotes for all tracked tickers.

This endpoint does NOT use any AI agents — it calls yfinance directly and
returns raw market data for the landing page watchlist.

Phase 3: 60-second Redis TTL cache — avoids hammering yfinance on every request.
"""

import asyncio
from typing import Any

import yfinance as yf
from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from api.schemas.memo import StockQuote, StocksResponse
from core import redis as cache
from core.config import settings

router = APIRouter(prefix="/stocks", tags=["stocks"])

# Human-readable company names for the UI
_NAMES: dict[str, str] = {
    "QUBT":  "Quantum Computing Inc.",
    "IONQ":  "IonQ Inc.",
    "RGTI":  "Rigetti Computing",
    "QBTS":  "D-Wave Quantum",
    "NVDA":  "NVIDIA Corp.",
    "SMCI":  "Super Micro Computer",
    "MSTR":  "MicroStrategy",
    "ARQQ":  "Arqit Quantum",
    "IBM":  "IBM Quantum",
    "INTC":  "Intel Corp.",
}


def _fetch_quote(ticker: str) -> dict[str, Any]:
    """
    Synchronous yfinance call — runs in a thread pool so it doesn't block
    the FastAPI event loop.
    """
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="2d")

        if hist.empty:
            return {"ticker": ticker, "error": "no data"}

        last_price   = float(hist["Close"].iloc[-1])
        volume       = int(hist["Volume"].iloc[-1])
        change_pct   = None

        if len(hist) >= 2:
            prev_close = float(hist["Close"].iloc[-2])
            if prev_close > 0:
                change_pct = round(((last_price - prev_close) / prev_close) * 100, 2)

        # market_cap from fast_info (fast, no HTTP rate-limit concern)
        fi = t.fast_info
        market_cap = getattr(fi, "market_cap", None)
        if market_cap is not None:
            market_cap = float(market_cap)

        return {
            "ticker":     ticker,
            "price":      round(last_price, 4),
            "change_pct": change_pct,
            "market_cap": market_cap,
            "volume":     volume,
        }
    except Exception as exc:
        return {"ticker": ticker, "error": str(exc)}


def _build_response(raw_results: list[dict[str, Any]]) -> StocksResponse:
    quotes: list[StockQuote] = []
    for raw in raw_results:
        ticker: str = raw["ticker"]
        if "error" in raw:
            quotes.append(StockQuote(
                ticker=ticker,
                name=_NAMES.get(ticker, ticker),
                price=None,
                change_pct=None,
                market_cap=None,
                volume=None,
            ))
        else:
            quotes.append(StockQuote(
                ticker=ticker,
                name=_NAMES.get(ticker, ticker),
                price=raw["price"],
                change_pct=raw["change_pct"],
                market_cap=raw["market_cap"],
                volume=raw["volume"],
            ))
    return StocksResponse(stocks=quotes)


@router.get("", response_model=StocksResponse, summary="Live quotes for all tracked tickers")
async def get_stocks() -> StocksResponse:
    """
    Returns current price, % change, market cap, and volume for every tracked
    ticker.

    Responses are cached in Redis for 60 seconds — the cache is shared across
    all concurrent requests so yfinance is called at most once per minute.
    """
    # --- Cache check ---
    cached = await cache.get_json(cache.STOCKS_KEY)
    if cached is not None:
        return StocksResponse(stocks=[StockQuote(**q) for q in cached])

    # --- Cache miss: fetch from yfinance ---
    tickers = settings.tracked_tickers
    raw_results: list[dict[str, Any]] = await asyncio.gather(
        *[run_in_threadpool(_fetch_quote, t) for t in tickers]
    )

    response = _build_response(raw_results)

    # --- Populate cache ---
    await cache.set_json(
        cache.STOCKS_KEY,
        [q.model_dump() for q in response.stocks],
        ttl=cache.STOCKS_TTL,
    )

    return response
