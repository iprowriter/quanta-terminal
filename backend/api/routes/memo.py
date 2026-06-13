"""
Memo routes
POST /api/v1/memo/{ticker}/generate  →  SSE stream of pipeline progress + final memo
GET  /api/v1/memo/{ticker}           →  fetch latest memo (Redis → Supabase fallback)

Auth
────
- GET  is public — anyone can read a cached memo.
- POST requires a valid Supabase JWT (magic-link login).
  The authenticated user's ID is recorded on the saved memo row.
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from agents.graph import stream_pipeline
from api.dependencies import CurrentUser, get_current_user
from api.schemas.memo import MemoRecord
from core import database as db
from core import redis as cache
from core.config import settings
from core.rate_limit import check_memo_limit

router = APIRouter(prefix="/memo", tags=["memo"])

# Human-friendly labels shown in the frontend progress UI
_AGENT_LABELS: dict[str, str] = {
    "sec":         "SEC Filings",
    "earnings":    "Earnings",
    "analyst":     "Analyst & Valuation",
    "news":        "News & Sentiment",
    "research":    "Research & Technology",
    "memo_writer": "Writing Memo",
}


def _validate_ticker(ticker: str) -> str:
    ticker = ticker.strip().upper()
    if ticker not in settings.tracked_tickers:
        raise HTTPException(
            status_code=400,
            detail=f"'{ticker}' is not a tracked ticker. Tracked: {settings.tracked_tickers}",
        )
    return ticker


@router.post(
    "/{ticker}/generate",
    summary="Generate investment memo (SSE) — requires auth",
    response_class=StreamingResponse,
    dependencies=[Depends(get_current_user)],   # 401 if no valid JWT
)
async def generate_memo(ticker: str, user: CurrentUser) -> StreamingResponse:
    """
    Triggers the full 5-agent pipeline and streams progress events back via
    Server-Sent Events (SSE).

    Requires: ``Authorization: Bearer <supabase_access_token>``

    **Event stream format** — each event is a JSON object on a ``data:`` line:

    ```
    data: {"event": "agent_complete", "agent": "sec", "label": "SEC Filings"}
    data: {"event": "agent_complete", "agent": "earnings", "label": "Earnings"}
    ...
    data: {"event": "memo_complete", "ticker": "QUBT", "memo": "...", "date": "..."}
    ```

    On completion the memo is:
    1. Persisted to Supabase (``memos`` table) with the requesting user's ID.
    2. Written to Redis with a 24-hour TTL so subsequent GET requests are fast.
    """
    ticker = _validate_ticker(ticker)
    user_id: str = user["id"]

    # Rate limit: 5 memo generations per user per day
    await check_memo_limit(user_id)

    async def _event_stream():
        try:
            async for event in stream_pipeline(ticker):
                # Enrich agent_complete events with a human-readable label
                if event.get("event") == "agent_complete":
                    event["label"] = _AGENT_LABELS.get(event["agent"], event["agent"])

                # On completion: persist + cache
                if event.get("event") == "memo_complete":
                    memo_data = {k: event.get(k, "") for k in (
                        "sec_analysis", "earnings_analysis", "analyst_analysis",
                        "news_analysis", "tech_analysis",
                    )}
                    # Fire-and-forget: don't let persistence errors block the stream
                    saved = await db.save_memo(
                        ticker=ticker,
                        memo=event.get("memo", ""),
                        date=event.get("date", ""),
                        user_id=user_id,
                        **memo_data,
                    )
                    await cache.set_json(
                        cache.memo_key(ticker),
                        saved or event,
                        ttl=cache.MEMO_TTL,
                    )

                yield f"data: {json.dumps(event)}\n\n"

        except Exception as exc:
            error_event = {"event": "error", "message": str(exc)}
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",       # disables Nginx response buffering
            "Connection":        "keep-alive",
        },
    )


@router.get(
    "/{ticker}",
    response_model=MemoRecord,
    summary="Get latest memo (public)",
    responses={404: {"description": "No memo found for this ticker"}},
)
async def get_memo(ticker: str) -> MemoRecord:
    """
    Returns the most recently generated memo for *ticker*.

    Lookup order:
    1. **Redis** (24-hour TTL) — sub-millisecond response
    2. **Supabase** — persistent storage, populates Redis on hit
    3. **404** — no memo generated yet; call POST .../generate first
    """
    ticker = _validate_ticker(ticker)

    # 1. Redis cache
    cached = await cache.get_json(cache.memo_key(ticker))
    if cached:
        return MemoRecord(**cached)

    # 2. Supabase
    row = await db.get_latest_memo(ticker)
    if row:
        # Back-fill Redis so future hits are instant
        await cache.set_json(cache.memo_key(ticker), row, ttl=cache.MEMO_TTL)
        return MemoRecord(**row)

    raise HTTPException(
        status_code=404,
        detail=f"No memo found for {ticker}. Use POST /{ticker}/generate to create one.",
    )
