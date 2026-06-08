"""
Auth routes
GET /api/v1/auth/me  →  returns the current user's profile from their JWT.

Note: We do NOT handle magic-link sending here — that's done entirely on the
frontend via the Supabase JS client:

    supabase.auth.signInWithOtp({ email })   // sends the magic link
    supabase.auth.getSession()               // returns the JWT after click

The backend only needs to *verify* the JWT on protected routes.
This route is a simple "who am I?" convenience endpoint.
"""

from fastapi import APIRouter

from api.dependencies import CurrentUser

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", summary="Get current user profile")
async def me(user: CurrentUser) -> dict:
    """
    Returns the authenticated user's profile decoded from their JWT.

    Requires: ``Authorization: Bearer <supabase_access_token>``

    The frontend obtains the token via:
        const { data: { session } } = await supabase.auth.getSession()
        // session.access_token  ← send this as the Bearer token
    """
    return {
        "id":    user["id"],
        "email": user["email"],
    }
