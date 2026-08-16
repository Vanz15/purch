"""Postgres/Supabase backend for the shared `db.models` layer.

This module implements every function `agent/`, `llm/`, and the
Streamlit/Reflex shells consume from `db.models` and `db.connection`,
against a Supabase-compatible Postgres via SQLAlchemy `text()` with
bound parameters. Signatures match the SQLite implementations exactly
so callers never notice which backend is active.

Selection is driven purely by env: if `REFLEX_DB_URL` or `DB_URL` is
set, `apply_patch_if_needed()` swaps the Postgres implementations into
the already-imported `db.models` / `db.connection` module namespaces
(before any agent code imports names from them). If neither is set,
the SQLite fallback is left in place — nothing is patched.

Runtime rules honored here:
    * NO DDL — we never create, alter, migrate, or seed tables. The
      schema is managed out-of-band by Supabase.
    * NO auto-init — `init_db()` becomes a no-op under Postgres.
    * Every value is bound via `text(...)` params — no string
      interpolation of user data ever reaches the SQL string.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# ---------------------------------------------------------------------------
# Engine selection
# ---------------------------------------------------------------------------

_PG_URL_RAW: str | None = os.getenv("REFLEX_DB_URL") or os.getenv("DB_URL")
USE_POSTGRES: bool = bool(_PG_URL_RAW)

_engine: Engine | None = None


def _normalize_url(url: str) -> str:
    """Rewrite legacy `postgres://` to `postgresql://` (SQLAlchemy needs
    the modern scheme). Leaves everything else alone."""
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://") :]
    return url


def get_engine() -> Engine:
    """Lazily build and cache the SQLAlchemy engine for Postgres.

    `pool_pre_ping` transparently reconnects when Supabase's pooler
    drops idle connections; the short `pool_recycle` keeps us well
    under its inactivity window.
    """
    global _engine
    if _engine is not None:
        return _engine
    if not _PG_URL_RAW:
        raise RuntimeError(
            "Postgres engine requested but neither REFLEX_DB_URL nor DB_URL is set."
        )
    # Short connect + statement timeouts are the single most important knob
    # for websocket stability on Reflex: a slow/hung DB call otherwise holds
    # the state lock past the websocket ping window and kills the session.
    # 5s connect / 8s statement means every read either returns fast, or
    # raises quickly enough that we can render a safe error and unwind
    # `is_loading` before the frontend gives up.
    _engine = create_engine(
        _normalize_url(_PG_URL_RAW),
        pool_pre_ping=True,
        pool_recycle=180,
        pool_size=5,
        max_overflow=10,
        pool_timeout=6,
        future=True,
        connect_args={
            "connect_timeout": 5,
            "options": "-c statement_timeout=8000 -c idle_in_transaction_session_timeout=8000",
        },
    )
    return _engine


# ---------------------------------------------------------------------------
# Value coercion helpers
# ---------------------------------------------------------------------------

_PH_OFFSET = timedelta(hours=8)


def _to_float(v: object) -> float:
    """NUMERIC columns come back as Decimal — normalize to float so the
    UI/agent never has to reason about it."""
    if v is None:
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _to_local_time_str(v: object) -> str:
    """Match the shape of `db.models.to_local_time_str` — accepts either
    a stored string (legacy SQLite path) or a `datetime` (Postgres) and
    returns a Philippines-local `YYYY-MM-DD HH:MM` string."""
    if v is None:
        return ""
    if isinstance(v, str):
        try:
            dt = datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            try:
                dt = datetime.fromisoformat(v)
            except ValueError:
                return v
    elif isinstance(v, datetime):
        dt = v
    else:
        return str(v)
    return (dt + _PH_OFFSET).strftime("%Y-%m-%d %H:%M")


# ---------------------------------------------------------------------------
# db.connection replacements
# ---------------------------------------------------------------------------


def pg_init_db() -> None:
    """No-op under Postgres — the Supabase schema is managed externally
    and we're forbidden from running DDL at runtime."""
    return None


def pg_ensure_user(user_id: str) -> None:
    """Idempotent user upsert (row created only on first sight)."""
    if not user_id:
        return
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (id) VALUES (:id) "
                "ON CONFLICT (id) DO NOTHING"
            ),
            {"id": user_id},
        )


# ---------------------------------------------------------------------------
# db.models replacements
# ---------------------------------------------------------------------------


def pg_insert_transaction(
    user_id: str,
    raw_text: str,
    item: str,
    amount: float,
    category: str,
    tx_date: Optional[str] = None,
) -> int:
    if amount is None or float(amount) <= 0:
        raise ValueError(f"amount must be positive, got {amount}")
    if not item or not category:
        raise ValueError("item and category cannot be empty")

    engine = get_engine()
    params: dict[str, object] = {
        "user_id": user_id,
        "raw_text": raw_text,
        "item": item,
        "amount": float(amount),
        "category": category,
    }
    if tx_date:
        params["ts"] = f"{tx_date} 12:00:00"
        sql = (
            "INSERT INTO transactions "
            "(user_id, raw_text, item, amount, category, tx_timestamp) "
            "VALUES (:user_id, :raw_text, :item, :amount, :category, "
            "(:ts)::timestamp) "
            "RETURNING id"
        )
    else:
        sql = (
            "INSERT INTO transactions "
            "(user_id, raw_text, item, amount, category) "
            "VALUES (:user_id, :raw_text, :item, :amount, :category) "
            "RETURNING id"
        )
    with engine.begin() as conn:
        row = conn.execute(text(sql), params).first()
    if row is None:
        raise RuntimeError("Insert did not return an id")
    return int(row[0])


def pg_get_recent_transactions(user_id: str, limit: int = 10) -> list[dict]:
    engine = get_engine()
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                "SELECT id, item, amount, category, tx_timestamp "
                "FROM transactions WHERE user_id = :uid "
                "ORDER BY tx_timestamp DESC LIMIT :lim"
            ),
            {"uid": user_id, "lim": int(limit)},
        ).all()
    out: list[dict] = []
    for r in rows:
        out.append(
            {
                "id": int(r[0]),
                "item": r[1],
                "amount": _to_float(r[2]),
                "category": r[3],
                "tx_timestamp": _to_local_time_str(r[4]),
            }
        )
    return out


def pg_get_user_tone(user_id: str) -> str:
    engine = get_engine()
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT tone_pref FROM users WHERE id = :uid"),
            {"uid": user_id},
        ).first()
    return row[0] if row and row[0] else "neutral"


def pg_set_user_tone(user_id: str, tone: str) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE users SET tone_pref = :tone WHERE id = :uid"),
            {"uid": user_id, "tone": tone},
        )


def pg_query_transactions(
    user_id: str,
    category: Optional[str] = None,
    category_mode: str = "include",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = None,
    item_hint: Optional[str] = None,
) -> dict:
    """Filtered transaction fetch. Returns the same shape as the SQLite
    implementation: `{transactions, total, count}`.

    Fixed SQL fragments (never raw user input) are spliced into the
    WHERE clause; every value goes through bound parameters."""
    where = ["user_id = :uid"]
    params: dict[str, object] = {"uid": user_id}

    if item_hint:
        where.append("item ILIKE :hint")
        params["hint"] = f"%{item_hint}%"
    if category:
        if category_mode == "exclude":
            where.append("category <> :cat")
        else:
            where.append("category = :cat")
        params["cat"] = category
    if start_date:
        where.append("tx_timestamp >= (:sd)::timestamp")
        params["sd"] = start_date
    if end_date:
        where.append("tx_timestamp < ((:ed)::date + INTERVAL '1 day')")
        params["ed"] = end_date

    sql = (
        "SELECT item, amount, category, tx_timestamp "
        "FROM transactions WHERE "
        + " AND ".join(where)
        + " ORDER BY tx_timestamp DESC"
    )
    if limit:
        sql += " LIMIT :lim"
        params["lim"] = int(limit)

    engine = get_engine()
    with engine.begin() as conn:
        rows = conn.execute(text(sql), params).all()

    txs: list[dict] = []
    for r in rows:
        txs.append(
            {
                "item": r[0],
                "amount": _to_float(r[1]),
                "category": r[2],
                "tx_timestamp": _to_local_time_str(r[3]),
            }
        )
    total = sum(t["amount"] for t in txs)
    return {"transactions": txs, "total": total, "count": len(txs)}


def pg_set_budget(
    user_id: str,
    category: str,
    limit_amount: float,
    period: str = "monthly",
) -> None:
    if limit_amount is None or float(limit_amount) <= 0:
        raise ValueError("limit_amount must be positive")
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO budgets (user_id, category, limit_amount, period) "
                "VALUES (:uid, :cat, :amt, :period) "
                "ON CONFLICT (user_id, category, period) "
                "DO UPDATE SET limit_amount = EXCLUDED.limit_amount"
            ),
            {
                "uid": user_id,
                "cat": category,
                "amt": float(limit_amount),
                "period": period,
            },
        )


def pg_get_budget(
    user_id: str, category: str, period: str = "monthly"
) -> Optional[float]:
    engine = get_engine()
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT limit_amount FROM budgets "
                "WHERE user_id = :uid AND category = :cat AND period = :period"
            ),
            {"uid": user_id, "cat": category, "period": period},
        ).first()
    if row is None or row[0] is None:
        return None
    return _to_float(row[0])


def pg_get_month_spent(user_id: str, category: str) -> float:
    start_of_month = date.today().replace(day=1).isoformat()
    engine = get_engine()
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT COALESCE(SUM(amount), 0) FROM transactions "
                "WHERE user_id = :uid AND category = :cat "
                "AND tx_timestamp >= (:som)::timestamp"
            ),
            {"uid": user_id, "cat": category, "som": start_of_month},
        ).first()
    return _to_float(row[0]) if row else 0.0


def pg_get_transaction_by_id(tx_id: int) -> Optional[dict]:
    engine = get_engine()
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT id, item, amount, category, tx_timestamp "
                "FROM transactions WHERE id = :id"
            ),
            {"id": int(tx_id)},
        ).first()
    if row is None:
        return None
    return {
        "id": int(row[0]),
        "item": row[1],
        "amount": _to_float(row[2]),
        "category": row[3],
        "tx_timestamp": _to_local_time_str(row[4]),
    }


def pg_find_best_match_transaction(
    user_id: str, item_hint: Optional[str] = None, limit: int = 5
) -> list[dict]:
    where = ["user_id = :uid"]
    params: dict[str, object] = {"uid": user_id, "lim": int(limit)}
    if item_hint:
        where.append("item ILIKE :hint")
        params["hint"] = f"%{item_hint}%"
    sql = (
        "SELECT id, item, amount, category, tx_timestamp "
        "FROM transactions WHERE "
        + " AND ".join(where)
        + " ORDER BY tx_timestamp DESC LIMIT :lim"
    )
    engine = get_engine()
    with engine.begin() as conn:
        rows = conn.execute(text(sql), params).all()
    return [
        {
            "id": int(r[0]),
            "item": r[1],
            "amount": _to_float(r[2]),
            "category": r[3],
            "tx_timestamp": _to_local_time_str(r[4]),
        }
        for r in rows
    ]


def pg_update_transaction(
    tx_id: int,
    item: Optional[str] = None,
    amount: Optional[float] = None,
    category: Optional[str] = None,
) -> None:
    if amount is not None and float(amount) <= 0:
        raise ValueError("amount must be positive")

    sets: list[str] = []
    params: dict[str, object] = {"id": int(tx_id)}
    if item is not None:
        sets.append("item = :item")
        params["item"] = item
    if amount is not None:
        sets.append("amount = :amount")
        params["amount"] = float(amount)
    if category is not None:
        sets.append("category = :category")
        params["category"] = category
    if not sets:
        return
    sql = "UPDATE transactions SET " + ", ".join(sets) + " WHERE id = :id"
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(sql), params)


def pg_delete_transaction(tx_id: int) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM transactions WHERE id = :id"),
            {"id": int(tx_id)},
        )


def pg_log_interaction(
    user_id: str,
    raw_message: str,
    intent: Optional[str],
    extracted: Optional[dict],
    response: Optional[str],
) -> None:
    """Best-effort logging — swallow errors so a logging hiccup can
    never break a chat turn."""
    try:
        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO interaction_log "
                    "(user_id, raw_message, intent, extracted_json, response) "
                    "VALUES (:uid, :raw, :intent, "
                    "CAST(:ej AS JSONB), :response)"
                ),
                {
                    "uid": user_id,
                    "raw": raw_message,
                    "intent": intent,
                    "ej": json.dumps(extracted) if extracted else None,
                    "response": response,
                },
            )
    except Exception as e:
        logging.exception(f"log_interaction failed: {e}")


def pg_get_all_budgets_and_spending(
    user_id: str, categories: list[str]
) -> dict:
    """One-pass fetch of {category: {limit, spent}} for every category."""
    start_of_month = date.today().replace(day=1).isoformat()
    engine = get_engine()
    with engine.begin() as conn:
        budget_rows = conn.execute(
            text(
                "SELECT category, limit_amount FROM budgets "
                "WHERE user_id = :uid AND period = 'monthly'"
            ),
            {"uid": user_id},
        ).all()
        spent_rows = conn.execute(
            text(
                "SELECT category, COALESCE(SUM(amount), 0) AS total "
                "FROM transactions "
                "WHERE user_id = :uid "
                "AND tx_timestamp >= (:som)::timestamp "
                "GROUP BY category"
            ),
            {"uid": user_id, "som": start_of_month},
        ).all()

    budget_map = {r[0]: _to_float(r[1]) for r in budget_rows}
    spent_map = {r[0]: _to_float(r[1]) for r in spent_rows}
    return {
        cat: {
            "limit": budget_map.get(cat),
            "spent": spent_map.get(cat, 0.0),
        }
        for cat in categories
    }


# ---------------------------------------------------------------------------
# Patch application
# ---------------------------------------------------------------------------


_PATCHED = False


def apply_patch_if_needed() -> bool:
    """When Postgres is configured, swap the Postgres implementations
    into `db.models` and `db.connection` module namespaces.

    Must be called BEFORE any consumer (`agent.nodes`, etc.) does
    `from db.models import <name>` — otherwise those consumers will
    have captured the SQLite implementations at import time and the
    patch won't reach them.

    Returns True if the patch was applied, False otherwise.
    """
    global _PATCHED
    if _PATCHED:
        return True
    if not USE_POSTGRES:
        return False

    try:
        import db.connection as _conn
        import db.models as _models
    except Exception as e:
        logging.exception(f"db.* modules unavailable — skipping patch: {e}")
        return False

    # Smoke-test the connection early so we fail loudly here instead of
    # deep inside an agent event. If the engine can't connect we leave
    # the SQLite bindings in place.
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        logging.exception(f"Postgres unreachable — keeping SQLite path: {e}")
        return False

    # db.connection: init_db becomes a no-op (schema is managed by
    # Supabase); ensure_user upserts via Postgres.
    _conn.init_db = pg_init_db  # type: ignore[assignment]
    _conn.ensure_user = pg_ensure_user  # type: ignore[assignment]

    # db.models: swap in every function agent/llm/shell consumers use.
    _models.insert_transaction = pg_insert_transaction  # type: ignore[assignment]
    _models.get_recent_transactions = pg_get_recent_transactions  # type: ignore[assignment]
    _models.get_user_tone = pg_get_user_tone  # type: ignore[assignment]
    _models.set_user_tone = pg_set_user_tone  # type: ignore[assignment]
    _models.query_transactions = pg_query_transactions  # type: ignore[assignment]
    _models.set_budget = pg_set_budget  # type: ignore[assignment]
    _models.get_budget = pg_get_budget  # type: ignore[assignment]
    _models.get_month_spent = pg_get_month_spent  # type: ignore[assignment]
    _models.get_transaction_by_id = pg_get_transaction_by_id  # type: ignore[assignment]
    _models.find_best_match_transaction = pg_find_best_match_transaction  # type: ignore[assignment]
    _models.update_transaction = pg_update_transaction  # type: ignore[assignment]
    _models.delete_transaction = pg_delete_transaction  # type: ignore[assignment]
    _models.log_interaction = pg_log_interaction  # type: ignore[assignment]
    _models.get_all_budgets_and_spending = pg_get_all_budgets_and_spending  # type: ignore[assignment]
    # to_local_time_str already handles both str and datetime — leave it.

    _PATCHED = True
    logging.info(
        "purch.db_backend: Postgres backend active — db.models patched."
    )
    return True
