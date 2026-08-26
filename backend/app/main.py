"""FastAPI entrypoint for the Purch backend.

- CORS allows the Vercel-deployed frontend (set via FRONTEND_ORIGIN env,
  or wide-open in dev). The Supabase JWT is still required on every
  protected route via app.deps.get_current_user_id.
- The Postgres/Supabase patch is applied at import (inside
  app.services.bootstrap) and the DB is bootstrapped once at startup via
  the lifespan handler — not as an import side effect.
"""
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Load .env (local dev). On Render the vars are injected into the process env,
# so this is a harmless no-op there. Load BEFORE any module reads os.environ.
from dotenv import load_dotenv

load_dotenv()

# Ensure the app package directory is on sys.path so the top-level packages
# `llm`, `agent`, and `db` (copied verbatim from the old repo, which imported
# them as bare names like `from llm import ...`) resolve alongside `app`.
_ROOT = str(Path(__file__).resolve().parent)  # backend/app
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Header

from app.routers import analytics, chat, tone, wallets, guest, transactions
from app.services import bootstrap

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("purch")

ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv("FRONTEND_ORIGIN", "").split(",")
    if o.strip()
]
# Dev convenience: allow localhost previews when no origin is configured.
if not ALLOWED_ORIGINS:
    ALLOWED_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Bootstrapping Purch backend...")
    bootstrap.bootstrap()
    if bootstrap.is_postgres():
        logger.info("Postgres/Supabase backend active.")
    else:
        logger.warning("Postgres not configured — SQLite fallback / degraded mode.")
    yield


app = FastAPI(title="Purch API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(wallets.router)
app.include_router(analytics.router)
app.include_router(tone.router)
app.include_router(guest.router)
app.include_router(transactions.router)


# TEMPORARY diagnostic — decodes ONLY the public claims of the incoming
# token (no secret handling, no token storage). Helps debug AUTH_REQUIRED.
# Remove after the issue is resolved.
@app.get("/_debug_token")
async def debug_token(authorization: str | None = Header(None)):
    from jose import jwt as _jwt
    if not authorization or not authorization.startswith("Bearer "):
        return {"ok": False, "reason": "no bearer"}
    token = authorization.removeprefix("Bearer ").strip()
    secret = os.environ.get("SUPABASE_JWT_SECRET", "")
    out = {"secret_present": bool(secret), "secret_len": len(secret)}
    # Decode WITHOUT verification to inspect claims (safe — no secret used).
    try:
        unverified = _jwt.get_unverified_claims(token)
        out["claims"] = {
            "iss": unverified.get("iss"),
            "aud": unverified.get("aud"),
            "email": unverified.get("email"),
            "sub": unverified.get("sub"),
            "exp": unverified.get("exp"),
            "role": unverified.get("role"),
        }
    except Exception as e:
        out["unverified_decode_error"] = str(e)
    # Now attempt verified decode to report the exact failure.
    if secret:
        try:
            _jwt.decode(token, secret, algorithms=["HS256"], audience="authenticated")
            out["verified"] = True
        except Exception as e:
            out["verified"] = False
            out["verify_error"] = str(e)
    return out


@app.get("/health")
async def health():
    return {"status": "ok", "postgres": bootstrap.is_postgres()}
