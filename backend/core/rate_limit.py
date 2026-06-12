"""
Redis-backed rate limiting.

Strategy: sliding window counter per (user_id, action) pair.
The key expires at midnight UTC so limits reset daily.

Usage
─────
    from core.rate_limit import check_rate_limit

    # In a route:
    await check_rate_limit(user_id=user["id"], action="memo_generate", limit=5)
    # Raises HTTP 429 if the user has exceeded `limit` calls today.
"""

import logging
from datetime import datetime, timezone, timedelta

from fastapi import HTTPException, status

from core import redis as cache

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Limits
# ---------------------------------------------------------------------------

MEMO_GENERATE_DAILY_LIMIT = 5   # memo generations per user per day
CHAT_HOURLY_LIMIT         = 60  # chat messages per user per hour


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seconds_until_midnight_utc() -> int:
    """Seconds remaining until next UTC midnight — used as TTL."""
    now  = datetime.now(timezone.utc)
    tomorrow = (now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return int((tomorrow - now).total_seconds())


def _memo_key(user_id: str) -> str:
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"rl:memo:{user_id}:{date}"


def _chat_key(user_id: str) -> str:
    hour = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H")
    return f"rl:chat:{user_id}:{hour}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def check_memo_limit(user_id: str) -> None:
    """
    Increment the daily memo generation counter for *user_id*.
    Raises HTTP 429 if the user has exceeded MEMO_GENERATE_DAILY_LIMIT today.
    """
    await _check(
        key=_memo_key(user_id),
        limit=MEMO_GENERATE_DAILY_LIMIT,
        ttl=_seconds_until_midnight_utc(),
        error_detail=(
            f"Daily memo generation limit reached ({MEMO_GENERATE_DAILY_LIMIT}/day). "
            "Limit resets at midnight UTC."
        ),
    )


async def check_chat_limit(user_id: str) -> None:
    """
    Increment the hourly chat counter for *user_id*.
    Raises HTTP 429 if the user has exceeded CHAT_HOURLY_LIMIT this hour.
    """
    await _check(
        key=_chat_key(user_id),
        limit=CHAT_HOURLY_LIMIT,
        ttl=3600,
        error_detail=(
            f"Chat rate limit reached ({CHAT_HOURLY_LIMIT}/hour). "
            "Please wait before sending more messages."
        ),
    )


async def _check(key: str, limit: int, ttl: int, error_detail: str) -> None:
    """
    Atomically increment *key* and raise 429 if the new count exceeds *limit*.
    Sets TTL on first use so the key auto-expires.
    """
    try:
        client = await cache._get_client()
        count  = await client.incr(key)
        if count == 1:
            # First request — set the expiry
            await client.expire(key, ttl)
        if count > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=error_detail,
                headers={"Retry-After": str(ttl)},
            )
    except HTTPException:
        raise
    except Exception as exc:
        # If Redis is down, fail open (don't block legitimate users)
        logger.warning("Rate limit check failed (Redis error): %s", exc)
