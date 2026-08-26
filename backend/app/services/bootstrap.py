"""Backend bootstrap for the Purch FastAPI service.

Consolidates what the old `purch/backend.py` did, but exposes a single
stable namespace (`app.services.bootstrap`) that the routers import —
instead of the old `purch.backend` package.

Load order is load-bearing (do NOT reorder):
  1. `install_safe_groq_calls()`
  2. `apply_patch_if_needed()` (swaps Postgres impls into db.models)
  3. then import the patched `db.models` / `agent.graph` names.

The old code also called `bootstrap()` at import time. We instead call
it explicitly from a FastAPI lifespan handler (see app/main.py) so the
DB setup happens once at process start, not as an import side effect.
"""

import logging

from app.services.groq_helper import install_safe_groq_calls
from app.services.time_utils import format_stored_timestamp

install_safe_groq_calls()

# IMPORTANT: apply the Postgres/Supabase patch BEFORE agent.* imports.
# `agent.nodes` does `from db.models import insert_transaction, get_user_tone`
# at module load, so the patch has to reach db.models first — otherwise
# the agent will have captured the SQLite implementations by name.
try:
    from app.services.db_backend import USE_POSTGRES, apply_patch_if_needed

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
        "Food", "Transport", "Bills", "Shopping", "Entertainment",
        "Health", "Personal Care", "Other",
    ]
    VALID_TONES = [
        "nonchalant", "bestie", "sarcastic", "coach", "rich tita", "kapampangan",
    ]

    def run_agent(user_id: str, message: str):  # type: ignore
        return {
            "response": "Backend unavailable.",
            "is_purchase": False, "intent": None, "item": None, "amount": None,
            "category": None, "currency": None, "transaction_id": None,
            "pending_edit": None, "pending_conversion": None, "tx_date": None,
        }

    def insert_transaction(*a, **k):  # type: ignore
        return 0
    def delete_transaction(*a, **k):  # type: ignore
        pass
    def update_transaction(*a, **k):  # type: ignore
        pass
    def get_all_budgets_and_spending(user_id, categories):  # type: ignore
        return {c: {"limit": None, "spent": 0.0} for c in categories}
    def get_user_tone(user_id):  # type: ignore
        return "nonchalant"
    def set_user_tone(user_id, tone):  # type: ignore
        pass
    def _generate_comment(*a, **k):  # type: ignore
        return ""
    def ensure_user(user_id):  # type: ignore
        pass
    def init_db():  # type: ignore
        pass


def generate_comment(item: str, amount: float, category: str, currency: str, tone: str) -> str:
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

    Under Postgres the patch (already applied at import) made `init_db()` a
    no-op — the Supabase schema is managed out-of-band and we're forbidden
    from running DDL at runtime. Under SQLite this still creates the local
    `data/budget.db` from `db/schema.sql`.
    """
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


def format_transaction_timestamp(value: object, timezone_name: str = "") -> str:
    return format_stored_timestamp(value, timezone_name)


def classify_alert(text: str) -> str:
    """Classify an assistant alert for the chat interface."""
    lower = text.lower()
    if "over your" in lower and "budget" in lower:
        return "danger"
    if "heads up" in lower or "almost" in lower or "⚠️" in text:
        return "warning"
    return ""
