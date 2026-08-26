"""Shared Groq completion guard for the phase-3 agent path."""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable


_MAX_ATTEMPTS = 2
_BASE_DELAY_SECONDS = 0.35
_MAX_SYSTEM_CHARS = 5200
_MAX_USER_CHARS = 1600

_THINKING_MODELS = ("openai/gpt-oss-120b", "openai/gpt-oss-20b")
_CONVERSATION_MODELS = ("llama-3.3-70b-versatile", "llama-3.1-8b-instant")
_MODEL_FALLBACKS = {
    _THINKING_MODELS[0]: _THINKING_MODELS,
    _THINKING_MODELS[1]: _THINKING_MODELS,
    _CONVERSATION_MODELS[0]: _CONVERSATION_MODELS,
    _CONVERSATION_MODELS[1]: _CONVERSATION_MODELS,
}


def _provider_status(exc: BaseException) -> str:
    status = getattr(exc, "status_code", None)
    if status is None:
        response = getattr(exc, "response", None)
        status = getattr(response, "status_code", None)
    return str(status) if isinstance(status, int) else "unknown"


def _is_provider_error(exc: BaseException) -> bool:
    """Identify SDK/HTTP failures without inspecting or logging their bodies."""
    module = type(exc).__module__.lower()
    name = type(exc).__name__.lower()
    status = _provider_status(exc)
    return (
        module.startswith("groq")
        or module.startswith("httpx")
        or module.startswith("httpcore")
        or hasattr(exc, "status_code")
        or hasattr(exc, "response")
        or status != "unknown"
        or name
        in {
            "apiconnectionerror",
            "apierror",
            "apitimeouterror",
            "badrequesterror",
            "connectionerror",
            "internalservererror",
            "ratelimiterror",
            "serviceunavailableerror",
            "timeouterror",
        }
    )


def _provider_category(exc: BaseException) -> str:
    name = type(exc).__name__.lower()
    status = _provider_status(exc)
    if status == "429" or "rate" in name:
        return "rate_limit"
    if status in {"408", "502", "503", "504"}:
        return "service_unavailable"
    if "timeout" in name:
        return "timeout"
    if "connection" in name:
        return "connection"
    if status.startswith("4"):
        return "client_error"
    if status.startswith("5"):
        return "provider_error"
    return "provider_error"


def _log_provider_failure(exc: BaseException, model: str, attempt: int) -> None:
    """Log only stable provider metadata; never serialize exception details."""
    logging.warning(
        "Groq completion failed: model=%s attempt=%d error_type=%s status=%s category=%s",
        model,
        attempt,
        type(exc).__name__,
        _provider_status(exc),
        _provider_category(exc),
    )


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

        requested_model = request.get("model")
        models = _MODEL_FALLBACKS.get(requested_model, (requested_model,))
        last_error: Exception | None = None

        for model_index, model in enumerate(models):
            if not isinstance(model, str) or not model:
                continue
            model_request = dict(request)
            model_request["model"] = model
            for attempt in range(_MAX_ATTEMPTS):
                try:
                    response = self._create(*args, **model_request)
                    if _response_is_usable(
                        response,
                        has_tools=bool(request.get("tools")),
                        model=model,
                        attempt=attempt + 1,
                    ):
                        return response
                    logging.warning(
                        "Groq returned an empty or length-limited response "
                        "for model=%s; trying the configured fallback.",
                        model,
                    )
                    last_error = RuntimeError(
                        "empty or length-limited Groq response"
                    )
                except Exception as exc:
                    last_error = exc
                    if _is_provider_error(exc):
                        # Provider exceptions can contain the full API response,
                        # so never pass them to logging.exception or exc_info.
                        _log_provider_failure(exc, model, attempt + 1)
                    else:
                        # Keep tracebacks for wrapper/coding failures, but do
                        # not interpolate exception text into the log message.
                        logging.exception(
                            "Groq wrapper internal error during completion"
                        )
                    if not _is_transient(exc):
                        raise
                if attempt < _MAX_ATTEMPTS - 1:
                    delay = _BASE_DELAY_SECONDS * (2**attempt)
                    time.sleep(delay + random.uniform(0, delay * 0.25))
            if model_index < len(models) - 1:
                logging.info(
                    "Groq switching to fallback model after bounded retries: model=%s next_model=%s",
                    model,
                    models[model_index + 1],
                )

        if last_error is not None:
            raise last_error
        raise RuntimeError(
            "Groq completion failed after bounded fallback attempts"
        )


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


def _response_is_usable(
    response: object,
    has_tools: bool,
    model: str,
    attempt: int,
) -> bool:
    """Reject provider responses that cannot safely drive the existing caller."""
    try:
        choices = getattr(response, "choices", None) or []
        if not choices:
            return False
        message = getattr(choices[0], "message", None)
        if message is None:
            return False
        tool_calls = getattr(message, "tool_calls", None)
        content = getattr(message, "content", None)
        finish_reason = getattr(choices[0], "finish_reason", None)
        # A length stop means the model did not complete the requested turn;
        # retrying on the backup model is safer than passing partial JSON or
        # truncated conversational text to the existing callers.
        if finish_reason == "length":
            return False
        if tool_calls:
            return True
        if isinstance(content, str) and content.strip():
            return True
        return not has_tools and bool(content)
    except Exception as exc:
        if _is_provider_error(exc):
            _log_provider_failure(exc, model, attempt)
        else:
            logging.exception("Groq response validation internal error")
        return False


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
                "overloaded",
                "server error",
                "internal server",
                "service unavailable",
                "temporarily unavailable",
                "502",
                "503",
                "504",
            )
        )
        or "timeout" in name
        or "connection" in name
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

    # Keep legacy tone helpers safe when callers pass the database default
    # ("neutral") or an unknown preference. The tone module normalizes to
    # this key before indexing its instruction map.
    tone.TONE_INSTRUCTIONS.setdefault(
        "neutral",
        """
Respond in plain, factual, professional English. No personality flair,
no jokes, no emojis. State the information clearly and briefly, like a
calm financial assistant. 1-2 sentences.
""",
    )

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
