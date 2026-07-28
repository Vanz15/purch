"""Backend bootstrap for the Purch Reflex shell.

Thin compatibility layer that (1) initializes the shared SQLite database
once at import time so the Reflex process is ready to serve chat, and
(2) re-exports the framework-agnostic business logic from the root
`agent/`, `llm/`, `db/` packages under a normalized `purch.backend`
namespace. The root packages remain the single source of truth — the
Streamlit fallback (`app.py`) continues to import them directly and
keeps working unchanged.
"""

import logging

try:
    from db.connection import ensure_user, init_db
    from db.models import (
        delete_transaction,
        get_all_budgets_and_spending,
        get_user_tone,
        insert_transaction,
        set_user_tone,
        update_transaction,
    )
    from llm.extraction import CATEGORIES
    from llm.tone import VALID_TONES, generate_comment

    from agent.graph import run_agent

    _BACKEND_AVAILABLE = True
    _BACKEND_ERROR = ""
except Exception as e:
    logging.exception(f"Backend import failed: {e}")
    _BACKEND_AVAILABLE = False
    _BACKEND_ERROR = str(e)
    CATEGORIES = [
        "Food",
        "Transport",
        "Bills",
        "Shopping",
        "Entertainment",
        "Health",
        "Personal Care",
        "Other",
    ]
    VALID_TONES = [
        "nonchalant",
        "bestie",
        "sarcastic",
        "coach",
        "rich tita",
        "kapampangan",
    ]

    def run_agent(user_id: str, message: str):  # type: ignore
        return {
            "response": "Backend unavailable.",
            "is_purchase": False,
            "intent": None,
            "item": None,
            "amount": None,
            "category": None,
            "currency": None,
            "transaction_id": None,
            "pending_edit": None,
            "pending_conversion": None,
            "tx_date": None,
        }

    def insert_transaction(*a, **k):
        return 0  # type: ignore

    def delete_transaction(*a, **k):
        pass  # type: ignore

    def update_transaction(*a, **k):
        pass  # type: ignore

    def get_all_budgets_and_spending(user_id, categories):  # type: ignore
        return {c: {"limit": None, "spent": 0.0} for c in categories}

    def get_user_tone(user_id):
        return "nonchalant"  # type: ignore

    def set_user_tone(user_id, tone):
        pass  # type: ignore

    def generate_comment(*a, **k):
        return ""  # type: ignore

    def ensure_user(user_id):
        pass  # type: ignore

    def init_db():
        pass  # type: ignore


_INITIALIZED = False


def bootstrap() -> None:
    """Initialize DB once per process. Safe to call repeatedly."""
    global _INITIALIZED
    if _INITIALIZED or not _BACKEND_AVAILABLE:
        return
    try:
        init_db()
        _INITIALIZED = True
    except Exception as e:
        logging.exception(f"DB init failed: {e}")


def is_available() -> bool:
    return _BACKEND_AVAILABLE


def classify_alert(text: str) -> str:
    """Port of app.py::classify_alert — decides bubble border color."""
    lower = text.lower()
    if "over your" in lower and "budget" in lower:
        return "danger"
    if "heads up" in lower or "almost" in lower or "⚠️" in text:
        return "warning"
    return ""


bootstrap()
