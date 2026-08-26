"""Guest identity endpoint.

The old Reflex app let users operate without a Supabase account by trusting a
client-supplied `user_email` from localStorage. This migration keeps the
backend as the sole auth authority: instead of trusting a raw email string,
the browser asks this endpoint for a short-lived JWT minted with the SAME
SUPABASE_JWT_SECRET Supabase uses, so get_current_user_id() verifies it
identically to a real Supabase session.

The token carries aud="authenticated" (required by our verify step), an
email/sub claim equal to the guest id, and a `guest: true` flag. Data written
with a guest id is isolated per guest id (the caller chooses the id).
"""

import os
import time
import uuid

from fastapi import APIRouter, HTTPException
from jose import jwt
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["guest"])

SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")
JWT_EXP_SECONDS = 60 * 60 * 24 * 7  # 7 days


class GuestRequest(BaseModel):
    guest_id: str | None = None


@router.post("/guest-token")
def guest_token(body: GuestRequest):
    if not SUPABASE_JWT_SECRET:
        raise HTTPException(status_code=500, detail="Server auth not configured")

    guest_id = (body.guest_id or "").strip()
    # Guest ids must be namespaced + non-empty so they can never collide with a
    # real Supabase email identity.
    if not guest_id or not guest_id.startswith("guest-"):
        guest_id = f"guest-{uuid.uuid4().hex}"

    now = int(time.time())
    payload = {
        "sub": guest_id,
        "email": guest_id,
        "aud": "authenticated",
        "role": "authenticated",
        "guest": True,
        "iat": now,
        "exp": now + JWT_EXP_SECONDS,
    }
    token = jwt.encode(payload, SUPABASE_JWT_SECRET, algorithm="HS256")
    return {"access_token": token, "guest_id": guest_id}
