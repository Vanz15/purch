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


class EmailAlreadyRegisteredError(RuntimeError):
    """Raised when a signup attempt targets an email that already has an
    account. Kept as a distinct type so the UI layer can render a
    specific message without doing brittle string matching on the raw
    Supabase error."""


def sign_up_with_password(
    email: str, password: str, display_name: str | None
) -> dict[str, str]:
    """Create an account with email + password.

    Behavior notes:
      * If the email is already registered, raise
        `EmailAlreadyRegisteredError` instead of silently "succeeding".
        Supabase (with email-confirmations on) returns a `User` with an
        empty `identities` list for pre-existing accounts as a privacy
        feature — we detect that shape here so callers can show a
        clear "email already in use" message rather than sending the
        user through an infinite confirmation loop.
      * On real success returns `{user_id, email, name}`.
    """
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

    # Supabase's "confirm email" flow returns a synthetic user with no
    # identities when the address is already registered. Treat that as a
    # duplicate — creating a second account is not possible and the user
    # deserves to know.
    identities = getattr(user, "identities", None)
    if isinstance(identities, list) and len(identities) == 0:
        raise EmailAlreadyRegisteredError(
            "An account with that email already exists."
        )

    meta = getattr(user, "user_metadata", {}) or {}
    return {
        "user_id": str(user.id),
        "email": str(user.email or email),
        "name": str(meta.get("display_name") or display_name or ""),
    }


def send_password_reset_email(
    email: str, redirect_to: str | None = None
) -> None:
    """Trigger Supabase's password-recovery email. Raises on transport
    failure; success is signalled by returning normally. Supabase
    intentionally does not disclose whether the address exists, so we
    surface a neutral "if that email exists, we sent a link" message
    in the UI regardless."""
    client = get_client()
    options: dict[str, Any] = {}
    if redirect_to:
        options["redirect_to"] = redirect_to
    # supabase-py exposes this as `reset_password_email` in older
    # releases and `reset_password_for_email` in newer ones — call
    # whichever exists so both work.
    fn = getattr(client.auth, "reset_password_for_email", None) or getattr(
        client.auth, "reset_password_email", None
    )
    if fn is None:
        raise RuntimeError("Password reset isn't available on this server.")
    if options:
        fn(email, options)
    else:
        fn(email)


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
    if isinstance(exc, EmailAlreadyRegisteredError):
        return (
            "That email is already in use. Try signing in instead, "
            "or use \u201cForgot password?\u201d to recover access."
        )
    try:
        raw = str(exc).lower()
    except Exception:
        logging.exception("Unexpected error stringifying auth exception")
        raw = ""
    # Rate limiting — check BEFORE generic "invalid login" mapping so
    # Supabase's "email rate limit exceeded" / HTTP 429 responses
    # surface as a clear rate-limit notice instead of a generic error.
    if (
        "rate limit" in raw
        or "too many" in raw
        or "429" in raw
        or "over_email_send_rate_limit" in raw
        or "email rate limit" in raw
    ):
        if "email" in raw:
            return (
                "We've sent too many emails to that address recently. "
                "Please wait a few minutes before trying again."
            )
        return "Too many attempts — please wait a minute and try again."
    if "invalid login" in raw or "invalid credentials" in raw:
        return "That email and password combination didn't match."
    if "email not confirmed" in raw:
        return "Please confirm your email before signing in."
    if (
        "already registered" in raw
        or "user already" in raw
        or "already exists" in raw
        or "already been registered" in raw
    ):
        return (
            "That email is already in use. Try signing in instead, "
            "or use \u201cForgot password?\u201d to recover access."
        )
    if "password" in raw and (
        "short" in raw or "at least" in raw or "weak" in raw
    ):
        return "Please choose a longer password (at least 6 characters)."
    if "network" in raw or "connection" in raw or "timeout" in raw:
        return "Couldn't reach the auth service just now. Please try again."
    return "Sorry, we couldn't complete that just now. Please try again."
