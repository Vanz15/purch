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

from purch.groq_helper import install_safe_groq_calls

install_safe_groq_calls()

# IMPORTANT: apply the Postgres/Supabase patch BEFORE agent.* imports.
# `agent.nodes` does `from db.models import insert_transaction, get_user_tone`
# at module load, so the patch has to reach db.models first — otherwise
# the agent will have captured the SQLite implementations by name.
try:
    from purch.db_backend import USE_POSTGRES, apply_patch_if_needed

    _POSTGRES_ACTIVE = apply_patch_if_needed()
except Exception as e:
    logging.exception(f"Postgres patch failed to apply: {e}")
    USE_POSTGRES = False
    _POSTGRES_ACTIVE = False

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
    from llm.tone import VALID_TONES, generate_comment as _generate_comment

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

    def _generate_comment(*a, **k):
        return ""  # type: ignore

    def ensure_user(user_id):
        pass  # type: ignore

    def init_db():
        pass  # type: ignore


def generate_comment(
    item: str, amount: float, category: str, currency: str, tone: str
) -> str:
    """Generate a tone reaction while treating neutral/default as no reaction."""
    if tone not in VALID_TONES:
        return ""
    try:
        return _generate_comment(item, amount, category, currency, tone)
    except Exception as e:
        logging.exception(f"Comment generation failed: {e}")
        return ""


_INITIALIZED = False


def bootstrap() -> None:
    """Prepare the DB layer once per process. Safe to call repeatedly.

    Under Postgres the patch (already applied at module import) has made
    `init_db()` a no-op — the Supabase schema is managed out-of-band and
    we're forbidden from running DDL at runtime. Under SQLite this still
    creates the local `data/budget.db` from `db/schema.sql`."""
    global _INITIALIZED
    if _INITIALIZED or not _BACKEND_AVAILABLE:
        return
    try:
        init_db()
        _INITIALIZED = True
    except Exception as e:
        logging.exception(f"DB init failed: {e}")


def is_postgres() -> bool:
    """True iff the process is talking to Postgres/Supabase."""
    return bool(_POSTGRES_ACTIVE)


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
