"""
FastAPI dependencies for authentication.

Usage
─────
    from api.dependencies import get_current_user, CurrentUser

    @router.post("/protected")
    async def protected(user: CurrentUser) -> dict:
        return {"user_id": user["id"], "email": user["email"]}

For endpoints that accept both authenticated and anonymous requests,
use ``get_optional_user``:

    @router.get("/memo/{ticker}")
    async def get_memo(ticker: str, user: dict | None = Depends(get_optional_user)):
        ...
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.security import verify_supabase_jwt

# ---------------------------------------------------------------------------
# Bearer scheme — auto-generates the "Authorize" button in /docs
# ---------------------------------------------------------------------------

_bearer = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    """
    Require a valid Supabase JWT in the Authorization header.

    Returns a dict with at least:
        {
            "id":    "<supabase user uuid>",
            "email": "user@example.com",
        }

    Raises 401 if the header is missing or the token is invalid/expired.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_supabase_jwt(credentials.credentials)

    return {
        "id":    payload["sub"],
        "email": payload.get("email", ""),
        # Expose the full payload so routes can inspect role / app_metadata if needed
        "_raw": payload,
    }


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict | None:
    """
    Return user dict if a valid JWT is present, otherwise None.

    Useful for endpoints that work both authenticated and anonymously,
    e.g. reading a cached memo (public) vs generating one (private).
    """
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


# ---------------------------------------------------------------------------
# Annotated shorthand  (cleaner route signatures)
# ---------------------------------------------------------------------------

CurrentUser         = Annotated[dict,        Depends(get_current_user)]
OptionalCurrentUser = Annotated[dict | None, Depends(get_optional_user)]
