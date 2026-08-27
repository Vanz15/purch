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
import httpx

from fastapi import Header, HTTPException
import jwt as pyjwt

logger = logging.getLogger("purch.auth")

# Sanitize: env vars pasted into dashboards often pick up a trailing newline
# or stray whitespace, which breaks HS256 verification ("alg not allowed").
SUPABASE_JWT_SECRET = (os.environ.get("SUPABASE_JWT_SECRET", "") or "").strip()

# Supabase project reference (from SUPABASE_URL) for JWKS endpoint.
# e.g., if SUPABASE_URL=https://tzkkzhirrazfjqomiebp.supabase.co -> ref=tzkkzhirrazfjqomiebp
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_REF = SUPABASE_URL.rstrip("/").split("//")[-1].split(".")[0] if SUPABASE_URL else ""
JWKS_URL = f"https://{SUPABASE_REF}.supabase.co/auth/v1/.well-known/jwks.json" if SUPABASE_REF else ""

# In-memory JWKS cache (5 min TTL)
_jwks_cache = {"keys": None, "fetched_at": 0}


async def _get_jwks() -> dict:
    """Fetch and cache Supabase JWKS public keys."""
    import time
    now = time.time()
    if _jwks_cache["keys"] and now - _jwks_cache["fetched_at"] < 300:
        return _jwks_cache["keys"]
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(JWKS_URL)
        resp.raise_for_status()
        data = resp.json()
        _jwks_cache["keys"] = data.get("keys", [])
        _jwks_cache["fetched_at"] = now
        return _jwks_cache["keys"]


def _get_public_key_for_kid(kid: str, keys: list) -> str | None:
    """Find the JWKS key matching kid and return its PEM-encoded public key."""
    for key in keys:
        if key.get("kid") == kid:
            # Convert JWK to PEM for PyJWT
            return pyjwt.algorithms.ECAlgorithm.from_jwk(key)
    return None


async def get_current_user_id(authorization: str | None = Header(None)) -> str:
    """Return the verified user identity (email string) from the bearer token.

    Supports two token types:
    - Supabase-issued access tokens: ES256, verified via Supabase JWKS.
    - Backend-minted guest tokens: HS256, verified via SUPABASE_JWT_SECRET.

    Raises 401 when the header is missing, malformed, or the token is
    invalid / expired.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if not SUPABASE_JWT_SECRET:
        logger.error("SUPABASE_JWT_SECRET is not set — cannot verify tokens")
        raise HTTPException(status_code=500, detail="Server auth not configured")

    # Inspect header to determine algorithm & key id
    try:
        header = pyjwt.get_unverified_header(token)
    except Exception as e:
        logger.warning(f"JWT header decode failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid token header")

    alg = header.get("alg", "")
    kid = header.get("kid")

    # Supabase tokens: ES256 with kid -> verify via JWKS
    if alg == "ES256" and kid:
        try:
            keys = await _get_jwks()
            public_key = _get_public_key_for_kid(kid, keys)
            if not public_key:
                logger.warning(f"JWKS key not found for kid={kid}")
                raise HTTPException(status_code=401, detail="Invalid token key")
            payload = pyjwt.decode(
                token, public_key, algorithms=["ES256"], audience="authenticated"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"JWT verification failed (ES256): {e}")
            raise HTTPException(status_code=401, detail="Invalid or expired token")
    # Guest tokens (or any HS256): verify with secret
    else:
        try:
            payload = pyjwt.decode(
                token, SUPABASE_JWT_SECRET, algorithms=["HS256"], audience="authenticated"
            )
        except Exception as e:
            logger.warning(f"JWT verification failed (HS256): {e}")
            raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("email") or payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing user identity")
    return str(user_id)