"""
JWT verification for Supabase magic-link auth.

Supabase newer projects use ES256 (Elliptic Curve) signed JWTs verified via
the project's JWKS endpoint. Older projects used HS256 signed with the JWT
secret. We support both by reading the algorithm from the token header.

  ES256 → fetch public key from {SUPABASE_URL}/auth/v1/.well-known/jwks.json
  HS256 → verify with SUPABASE_JWT_SECRET (legacy / self-hosted)

The JWKS is fetched once on first use and cached in memory.

Token anatomy
─────────────
{
  "aud": "authenticated",
  "exp": <unix timestamp>,
  "sub": "<user uuid>",
  "email": "user@example.com",
  "role": "authenticated",
  ...
}

Usage
─────
    from core.security import verify_supabase_jwt

    payload = verify_supabase_jwt(token)  # raises HTTPException on failure
    user_id = payload["sub"]
    email   = payload.get("email")
"""

import logging

import httpx
from fastapi import HTTPException, status
from jose import ExpiredSignatureError, JWTError, jwt

from core.config import settings

logger = logging.getLogger(__name__)

AUDIENCE = "authenticated"

# ---------------------------------------------------------------------------
# JWKS cache (ES256)
# ---------------------------------------------------------------------------

_jwks_cache: dict | None = None


def _get_jwks() -> dict:
    """
    Fetch Supabase's public JWKS and cache it for the process lifetime.
    Called once on the first ES256 token verification.
    """
    global _jwks_cache
    if _jwks_cache is None:
        url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
        try:
            response = httpx.get(url, timeout=10)
            response.raise_for_status()
            _jwks_cache = response.json()
            logger.info("Loaded Supabase JWKS (%d key(s))", len(_jwks_cache.get("keys", [])))
        except Exception as exc:
            logger.error("Failed to fetch Supabase JWKS: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Auth service temporarily unavailable",
            )
    return _jwks_cache


def _key_for_token(token: str) -> tuple[object, list[str]]:
    """
    Return (signing_key, [algorithm]) appropriate for this token.
    Reads the alg and kid from the unverified header.
    """
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    alg = header.get("alg", "HS256")

    if alg == "HS256":
        return settings.supabase_jwt_secret, ["HS256"]

    if alg == "ES256":
        kid = header.get("kid")
        jwks = _get_jwks()
        keys = jwks.get("keys", [])
        key = next((k for k in keys if k.get("kid") == kid), None)
        if key is None:
            # kid not in cache — could be a key rotation; clear cache and retry once
            global _jwks_cache
            _jwks_cache = None
            jwks = _get_jwks()
            keys = jwks.get("keys", [])
            key = next((k for k in keys if k.get("kid") == kid), None)
        if key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token signing key not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return key, ["ES256"]

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=f"Unsupported JWT algorithm: {alg}",
        headers={"WWW-Authenticate": "Bearer"},
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def verify_supabase_jwt(token: str) -> dict:
    """
    Decode and verify a Supabase-issued JWT (ES256 or HS256).

    Returns the decoded payload on success.
    Raises ``HTTPException(401)`` on any verification failure.
    """
    key, algorithms = _key_for_token(token)

    try:
        payload: dict = jwt.decode(
            token,
            key,
            algorithms=algorithms,
            audience=AUDIENCE,
        )
        if not payload.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload

    except ExpiredSignatureError:
        logger.warning("JWT expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired — please sign in again",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as exc:
        logger.warning("JWT verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
