"""Auth dependency for the FastAPI backend.

The old Reflex app trusted a client-supplied `user_email` stored in
rx.LocalStorage. Here the browser holds the Supabase session and sends the
Supabase **JWT access token** on every call; the backend verifies it and
derives the user identity itself.

Per Phase 2 findings: the live Supabase `transactions.user_id` /
`wallets.user_id` columns store the user's **email string** (sample
'aivannpmartinez@gmail.com'), exactly matching the old `auth.user_email`
convention — so we read `payload["email"]`, not `payload["sub"]`.

Supabase issues access tokens signed with **ES256** (asymmetric). We verify
them against Supabase's published JWKS public keys. Backend-minted guest
tokens are HS256 (shared secret) and fall back to SUPABASE_JWT_SECRET.
"""
import logging
import os

from fastapi import Header, HTTPException
from jwt import PyJWKClient, decode, get_unverified_header, InvalidTokenError

logger = logging.getLogger("purch.auth")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_JWT_SECRET = (os.environ.get("SUPABASE_JWT_SECRET", "") or "").strip()

# JWKS client for verifying Supabase-issued (ES256) tokens.
_jwks_client = (
    PyJWKClient(f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json")
    if SUPABASE_URL
    else None
)


async def get_current_user_id(authorization: str | None = Header(None)) -> str:
    """Return the verified user identity (email string) from the bearer token.

    Raises 401 when the header is missing, malformed, or the token is
    invalid / expired.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()

    # Determine algorithm from the token header.
    try:
        alg = get_unverified_header(token).get("alg", "ES256")
    except Exception:
        alg = "ES256"

    try:
        if alg == "HS256" and SUPABASE_JWT_SECRET:
            # Backend-minted guest token.
            payload = decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
            )
        elif _jwks_client is not None:
            # Supabase-issued token: verify against JWKS (ES256).
            signing_key = _jwks_client.get_signing_key_from_jwt(token)
            payload = decode(
                token,
                signing_key.key,
                algorithms=["ES256"],
                audience="authenticated",
            )
        else:
            logger.error("No JWKS client and no secret configured for auth")
            raise HTTPException(status_code=500, detail="Server auth not configured")
    except InvalidTokenError as e:
        logger.warning(f"JWT verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("email") or payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing user identity")
    return str(user_id)
