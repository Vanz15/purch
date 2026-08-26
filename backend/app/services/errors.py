"""Safe user-facing error messages for external API / backend failures.

The chat loop touches several external systems (Groq for LLM inference,
Supabase/Postgres for persistence, the LangGraph agent orchestration).
When any of those fail, raw exception strings can contain sensitive
material — API keys echoed back in error bodies, connection strings,
stack fragments — that must never reach the browser.

`safe_error_message(exc)` inspects the exception and returns a short,
friendly, deterministic string appropriate for a chat bubble. Detailed
diagnostics stay on the server via `logging.exception` at the call
site.
"""

from __future__ import annotations

import logging


def _lower(exc: BaseException) -> str:
    try:
        return str(exc).lower()
    except Exception:
        logging.exception("Unexpected error")
        return ""


def classify_error(exc: BaseException) -> str:
    """Return a stable category label for an exception.

    Categories: 'rate_limit' | 'auth' | 'credentials' | 'timeout' |
    'connection' | 'db' | 'unknown'.
    """
    msg = _lower(exc)
    name = type(exc).__name__.lower()

    if (
        "429" in msg
        or "rate limit" in msg
        or "too many requests" in msg
        or "quota" in msg
    ):
        return "rate_limit"
    if (
        "groq_api_key" in msg
        or "api key" in msg
        or "api_key" in msg
        or "credential" in msg
    ):
        return "credentials"
    if (
        "401" in msg
        or "unauthorized" in msg
        or "forbidden" in msg
        or "403" in msg
    ):
        return "auth"
    if "timeout" in msg or "timed out" in name or "timeouterror" in name:
        return "timeout"
    if (
        "connection" in msg
        or "connectionerror" in name
        or "operationalerror" in name
        or "network" in msg
    ):
        return "connection"
    if (
        "sqlalchemy" in msg
        or "database" in msg
        or "psycopg" in msg
        or "programmingerror" in name
        or "integrityerror" in name
    ):
        return "db"
    return "unknown"


_MESSAGES: dict[str, str] = {
    "rate_limit": (
        "The assistant is taking a quick breather — too many requests came in "
        "at once. Please try again in a minute."
    ),
    "credentials": (
        "The assistant isn't fully configured on the server right now. "
        "Please try again shortly."
    ),
    "auth": (
        "The assistant couldn't authenticate with its provider. "
        "Please try again in a moment."
    ),
    "timeout": (
        "That took longer than expected and timed out. Give it another try?"
    ),
    "connection": (
        "I couldn't reach the assistant just now — looks like a network hiccup. "
        "Please try again in a moment."
    ),
    "db": ("I couldn't save that to your history just now. Please try again."),
    "unknown": (
        "Something went sideways on my end. Please try again in a moment."
    ),
}


def safe_error_message(exc: BaseException) -> str:
    """Return a friendly, secret-free message for a chat bubble."""
    return _MESSAGES.get(classify_error(exc), _MESSAGES["unknown"])


def safe_banner_message(exc: BaseException) -> str:
    """Slightly terser variant for the inline composer error banner."""
    category = classify_error(exc)
    if category == "rate_limit":
        return "Rate limited — please try again in a minute."
    if category == "credentials":
        return "Assistant temporarily unavailable — try again shortly."
    if category == "auth":
        return "Assistant couldn't authenticate — try again in a moment."
    if category == "timeout":
        return "That request timed out. Try again?"
    if category == "connection":
        return "Network hiccup reaching the assistant. Try again?"
    if category == "db":
        return "Couldn't reach your history just now. Try again?"
    return "Something went wrong. Please try again."
