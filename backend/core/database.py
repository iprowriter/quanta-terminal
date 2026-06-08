"""
Supabase client — memo persistence.

The Supabase Python client (v2) is synchronous by default.
All DB calls are wrapped in `run_in_threadpool` so they don't block
the FastAPI async event loop.

Table schema: see supabase/migrations/001_create_memos.sql
"""

import logging
from typing import Any, cast

from starlette.concurrency import run_in_threadpool
from supabase import create_client, Client

from core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Client singleton
# ---------------------------------------------------------------------------

_client: Client | None = None


def _get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key,   # service role bypasses RLS for server writes
        )
    return _client


# ---------------------------------------------------------------------------
# Memo persistence
# ---------------------------------------------------------------------------

def _save_memo_sync(
    ticker: str,
    memo: str,
    date: str,
    sec_analysis: str,
    earnings_analysis: str,
    analyst_analysis: str,
    news_analysis: str,
    tech_analysis: str,
    user_id: str | None,
) -> dict[str, Any]:
    client = _get_client()
    row = {
        "ticker":            ticker,
        "memo":              memo,
        "date":              date,
        "sec_analysis":      sec_analysis,
        "earnings_analysis": earnings_analysis,
        "analyst_analysis":  analyst_analysis,
        "news_analysis":     news_analysis,
        "tech_analysis":     tech_analysis,
        "generated_by":      user_id,
    }
    response = client.table("memos").insert(row).execute()
    return cast(dict[str, Any], response.data[0]) if response.data else row


async def save_memo(
    ticker: str,
    memo: str,
    date: str,
    sec_analysis: str = "",
    earnings_analysis: str = "",
    analyst_analysis: str = "",
    news_analysis: str = "",
    tech_analysis: str = "",
    user_id: str | None = None,
) -> dict[str, Any]:
    """Insert a generated memo into the memos table. Returns the saved row."""
    try:
        return await run_in_threadpool(
            _save_memo_sync,
            ticker, memo, date,
            sec_analysis, earnings_analysis, analyst_analysis,
            news_analysis, tech_analysis,
            user_id,
        )
    except Exception as exc:
        logger.error("Failed to save memo for %s: %s", ticker, exc)
        return {}


def _get_latest_memo_sync(ticker: str) -> dict[str, Any] | None:
    client = _get_client()
    response = (
        client.table("memos")
        .select("*")
        .eq("ticker", ticker.upper())
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if response.data:
        return cast(dict[str, Any], response.data[0])
    return None


async def get_latest_memo(ticker: str) -> dict[str, Any] | None:
    """Return the most recently generated memo for *ticker*, or None."""
    try:
        return await run_in_threadpool(_get_latest_memo_sync, ticker)
    except Exception as exc:
        logger.error("Failed to fetch memo for %s: %s", ticker, exc)
        return None
