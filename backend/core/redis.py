"""
Redis client — async wrapper around redis.asyncio.

Usage
-----
    from core.redis import cache

    # Stock quotes (60-second TTL)
    data = await cache.get_json("stocks:all")
    await cache.set_json("stocks:all", payload, ttl=cache.STOCKS_TTL)

    # Memos (24-hour TTL)
    memo = await cache.get_json(cache.memo_key("QUBT"))
    await cache.set_json(cache.memo_key("QUBT"), memo_dict, ttl=cache.MEMO_TTL)
"""

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# TTL constants
# ---------------------------------------------------------------------------

STOCKS_TTL = 60          # 1 minute  — stock prices are near-real-time
MEMO_TTL   = 60 * 60 * 24  # 24 hours — memos are expensive to regenerate


# ---------------------------------------------------------------------------
# Key helpers
# ---------------------------------------------------------------------------

def memo_key(ticker: str) -> str:
    return f"memo:{ticker.upper()}"

STOCKS_KEY = "stocks:all"


# ---------------------------------------------------------------------------
# Client singleton
# ---------------------------------------------------------------------------

_client: aioredis.Redis | None = None


async def _get_client() -> aioredis.Redis:
    global _client
    if _client is None:
        _client = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
        )
    return _client


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

async def get_json(key: str) -> Any | None:
    """Return the deserialized value for *key*, or None on miss/error."""
    try:
        client = await _get_client()
        raw = await client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as exc:
        logger.warning("Redis GET failed for '%s': %s", key, exc)
        return None


async def set_json(key: str, value: Any, ttl: int) -> None:
    """Serialize *value* as JSON and store it with the given TTL (seconds)."""
    try:
        client = await _get_client()
        await client.setex(key, ttl, json.dumps(value))
    except Exception as exc:
        logger.warning("Redis SET failed for '%s': %s", key, exc)


async def delete(key: str) -> None:
    """Delete a key (e.g. to invalidate a stale memo)."""
    try:
        client = await _get_client()
        await client.delete(key)
    except Exception as exc:
        logger.warning("Redis DELETE failed for '%s': %s", key, exc)


async def ping() -> bool:
    """Return True if Redis is reachable. Used in the health check."""
    try:
        client = await _get_client()
        return await client.ping()
    except Exception:
        return False


async def close() -> None:
    """Close the connection pool — called at app shutdown."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
