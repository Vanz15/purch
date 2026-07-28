"""Shared Groq completion guard for the phase-3 agent path."""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable


_MAX_ATTEMPTS = 3
_BASE_DELAY_SECONDS = 0.35
_MAX_SYSTEM_CHARS = 5200
_MAX_USER_CHARS = 1600


class _SafeCompletions:
    def __init__(self, create: Callable[..., object]) -> None:
        self._create = create

    def create(self, *args: object, **kwargs: object) -> object:
        request = dict(kwargs)
        messages = request.get("messages")
        if isinstance(messages, list):
            request["messages"] = _trim_messages(messages)

        if "max_tokens" not in request:
            request["max_tokens"] = 256 if request.get("tools") else 160
        elif isinstance(request["max_tokens"], int):
            request["max_tokens"] = min(request["max_tokens"], 256)

        for attempt in range(_MAX_ATTEMPTS):
            try:
                return self._create(*args, **request)
            except Exception as exc:
                logging.exception(f"Groq completion attempt failed: {exc}")
                if not _is_transient(exc) or attempt == _MAX_ATTEMPTS - 1:
                    raise
                delay = _BASE_DELAY_SECONDS * (2**attempt)
                time.sleep(delay + random.uniform(0, delay * 0.25))
        raise RuntimeError("Groq completion failed after retries")


class _SafeChat:
    def __init__(self, completions: _SafeCompletions) -> None:
        self.completions = completions


class _SafeClient:
    def __init__(self, client: object) -> None:
        raw_chat = getattr(client, "chat")
        raw_completions = getattr(raw_chat, "completions")
        raw_create = getattr(raw_completions, "create")
        self.chat = _SafeChat(_SafeCompletions(raw_create))


def _trim_messages(messages: list[object]) -> list[object]:
    trimmed: list[object] = []
    for message in messages:
        if not isinstance(message, dict):
            trimmed.append(message)
            continue
        copy = dict(message)
        content = copy.get("content")
        if isinstance(content, str):
            limit = (
                _MAX_SYSTEM_CHARS
                if copy.get("role") == "system"
                else _MAX_USER_CHARS
            )
            normalized = " ".join(content.split())
            copy["content"] = normalized[:limit]
        trimmed.append(copy)
    return trimmed


def _is_transient(exc: BaseException) -> bool:
    text = str(exc).lower()
    name = type(exc).__name__.lower()
    return (
        any(
            marker in text
            for marker in (
                "429",
                "rate limit",
                "too many requests",
                "timeout",
                "timed out",
            )
        )
        or "timeout" in name
    )


_installed = False
_original_get_client: Callable[[], object] | None = None
_wrapped_clients: dict[int, _SafeClient] = {}


def install_safe_groq_calls() -> None:
    """Patch every phase-3 LLM module before the agent imports its symbols."""
    global _installed, _original_get_client
    if _installed:
        return

    from llm import (
        budget_extraction,
        edit_extraction,
        extraction,
        groq_client,
        intent,
    )
    from llm import query_extraction, tone

    if _original_get_client is None:
        _original_get_client = groq_client.get_client

    def safe_get_client() -> object:
        if _original_get_client is None:
            raise RuntimeError("Groq client bootstrap is unavailable")
        client = _original_get_client()
        key = id(client)
        if key not in _wrapped_clients:
            _wrapped_clients[key] = _SafeClient(client)
        return _wrapped_clients[key]

    groq_client.get_client = safe_get_client
    extraction.get_client = safe_get_client
    intent.get_client = safe_get_client
    query_extraction.get_client = safe_get_client
    budget_extraction.get_client = safe_get_client
    edit_extraction.get_client = safe_get_client
    tone.get_client = safe_get_client
    _installed = True
