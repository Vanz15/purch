"""Auth dependency for the FastAPI backend.

The old Reflex app trusted a client-supplied `user_email` stored in
rx.LocalStorage. Here the browser holds the Supabase session and sends the
Supabase **JWT access token** on every call; the backend verifies it and
derives the user identity itself.

Per Phase 2 findings: the live Supabase `transactions.user_id` /
`wallets.user_id` columns store the user's **email string** (sample
'aivannpmartinez@gmail.com'), exactly matching the old `auth.user_email`
convention — so we read `payload["email"]`, not `payload["sub"]`.
"""
import logging
import os

from fastapi import Header, HTTPException
from jose import jwt, JWTError

logger = logging.getLogger("purch.auth")

SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")


async def get_current_user_id(authorization: str | None = Header(None)) -> str:
    """Return the verified user identity (email string) from the bearer token.

    Raises 401 when the header is missing, malformed, or the token is
    invalid / expired.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if not SUPABASE_JWT_SECRET:
        # Misconfiguration on the server side, not a client error.
        logger.error("SUPABASE_JWT_SECRET is not set — cannot verify tokens")
        raise HTTPException(status_code=500, detail="Server auth not configured")
    try:
        payload = jwt.decode(
            token, SUPABASE_JWT_SECRET, algorithms=["HS256"], audience="authenticated"
        )
    except Exception as e:
        # Catches JWTError, DecodeError, ExpiredSignatureError, etc.
        logger.warning(f"JWT verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("email") or payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing user identity")
    return str(user_id)
