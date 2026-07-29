"""Supabase auth helper.

Wraps the small subset of `supabase-py` we need for the login screen so
the state class stays focused on UI orchestration and error mapping.
Secrets (`SUPABASE_URL`, `SUPABASE_KEY`) are read from the server-side
environment only — nothing here is ever serialized to the frontend.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from supabase import Client, create_client


_client: Client | None = None


def is_configured() -> bool:
    return bool(os.getenv("SUPABASE_URL")) and bool(os.getenv("SUPABASE_KEY"))


def get_client() -> Client:
    """Lazy singleton — building the client is cheap but we still avoid
    reconstructing on every event handler call."""
    global _client
    if _client is not None:
        return _client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("Supabase is not configured on the server.")
    _client = create_client(url, key)
    return _client


def build_google_oauth_url(redirect_to: str) -> str:
    """Ask Supabase for the Google OAuth authorize URL to redirect the
    browser to. Nothing user-provided is returned in this string — it's
    the provider's own hosted authorize endpoint."""
    client = get_client()
    resp: Any = client.auth.sign_in_with_oauth(
        {
            "provider": "google",
            "options": {"redirect_to": redirect_to},
        }
    )
    url = getattr(resp, "url", None)
    if not url:
        raise RuntimeError("Supabase did not return an OAuth URL.")
    return str(url)


def sign_up_with_password(
    email: str, password: str, display_name: str | None
) -> dict[str, str]:
    """Create an account with email + password. Returns a dict with
    keys: user_id, email, name. Raises on failure with a message safe
    for surface-level display (Supabase errors are already generic)."""
    client = get_client()
    data: dict[str, Any] = {"email": email, "password": password}
    if display_name:
        data["options"] = {"data": {"display_name": display_name}}
    resp = client.auth.sign_up(data)
    user = getattr(resp, "user", None)
    if user is None:
        raise RuntimeError(
            "Could not create the account. Please try a different email."
        )
    meta = getattr(user, "user_metadata", {}) or {}
    return {
        "user_id": str(user.id),
        "email": str(user.email or email),
        "name": str(meta.get("display_name") or display_name or ""),
    }


def sign_in_with_password(email: str, password: str) -> dict[str, str]:
    client = get_client()
    resp = client.auth.sign_in_with_password(
        {"email": email, "password": password}
    )
    user = getattr(resp, "user", None)
    if user is None:
        raise RuntimeError("Invalid email or password.")
    meta = getattr(user, "user_metadata", {}) or {}
    return {
        "user_id": str(user.id),
        "email": str(user.email or email),
        "name": str(meta.get("display_name") or meta.get("name") or ""),
    }


def exchange_code_for_session(code: str) -> dict[str, str]:
    """Complete the PKCE-style OAuth flow after Supabase redirects back
    with a `?code=…` query parameter."""
    client = get_client()
    resp = client.auth.exchange_code_for_session({"auth_code": code})
    user = getattr(resp, "user", None) or getattr(
        getattr(resp, "session", None), "user", None
    )
    if user is None:
        raise RuntimeError("Could not complete Google sign-in.")
    meta = getattr(user, "user_metadata", {}) or {}
    return {
        "user_id": str(user.id),
        "email": str(user.email or ""),
        "name": str(
            meta.get("full_name")
            or meta.get("name")
            or meta.get("display_name")
            or ""
        ),
    }


def safe_auth_error(exc: BaseException) -> str:
    """Map raw Supabase / network errors to a short user-facing string.
    Never echoes API keys, connection strings, or stack fragments."""
    try:
        raw = str(exc).lower()
    except Exception:
        logging.exception("Unexpected error stringifying auth exception")
        raw = ""
    if "invalid login" in raw or "invalid credentials" in raw:
        return "That email and password combination didn't match."
    if "email not confirmed" in raw:
        return "Please confirm your email before signing in."
    if "already registered" in raw or "user already" in raw:
        return "An account with that email already exists — try signing in."
    if "password" in raw and (
        "short" in raw or "at least" in raw or "weak" in raw
    ):
        return "Please choose a longer password (at least 6 characters)."
    if "rate limit" in raw or "too many" in raw:
        return "Too many attempts — please wait a minute and try again."
    if "network" in raw or "connection" in raw or "timeout" in raw:
        return "Couldn't reach the auth service just now. Please try again."
    return "Sorry, we couldn't complete that just now. Please try again."
