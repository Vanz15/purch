"""Wallet persistence helpers for Purch.

Talks to the connected Postgres/Supabase tables `wallets` and
`wallet_ledger`. When the process is running on the local SQLite
fallback we point the same SQLAlchemy code at `data/budget.db` — the SQL
here is deliberately written in a portable subset (no `now()`, no
`::casts`, no `ILIKE`) so both engines can run it unchanged.

Hard rules honored here:
  * NO DDL — this module never creates, alters, or migrates tables. If
    the wallet tables are missing (typical on the SQLite fallback) then
    `available()` returns False and the UI renders a friendly notice.
  * No account numbers, card numbers, or any sensitive account details
    are read or written. A wallet is only a nickname, a type, a balance,
    and an optional note.
"""

from __future__ import annotations

import difflib
import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

WALLET_TYPES: list[str] = [
    "Cash",
    "Bank",
    "Debt",
    "Loan",
    "Savings",
    "Lent",
    "Other",
]

# Words users naturally say that map onto a wallet type. Used for the
# cheap local match before we ever spend an LLM call.
TYPE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Cash": ("cash", "pera", "wallet cash", "on hand", "baon"),
    "Bank": ("bank", "gcash", "maya", "card", "online", "e-wallet", "ewallet"),
    "Savings": ("savings", "saving", "emergency fund", "fund"),
    "Debt": ("debt", "utang", "credit"),
    "Loan": ("loan", "loaned"),
    "Lent": ("lent", "lend", "pinautang"),
    "Other": ("other",),
}

# Only these wallet types can actually be spent from day-to-day. The
# sidebar mini summary shows exclusively these.
CONSUMABLE_TYPES: tuple[str, ...] = ("Cash", "Bank")

ASSET_TYPES: tuple[str, ...] = ("Cash", "Bank", "Savings", "Lent", "Other")
LIABILITY_TYPES: tuple[str, ...] = ("Debt", "Loan")

# Analytics grouping — Debit (what you hold), Lent (money out), Borrowed
# (money owed).
WALLET_GROUPS: dict[str, tuple[str, ...]] = {
    "Debit": ("Bank", "Cash", "Savings"),
    "Lent": ("Lent",),
    "Borrowed": ("Debt", "Loan"),
}
GROUP_ORDER: list[str] = ["Debit", "Lent", "Borrowed"]
GROUP_ACCENT: dict[str, str] = {
    "Debit": "teal",
    "Lent": "gold",
    "Borrowed": "danger",
}

TYPE_ACCENT: dict[str, str] = {
    "Cash": "teal",
    "Bank": "gold",
    "Savings": "teal",
    "Debt": "danger",
    "Loan": "danger",
    "Lent": "gold",
    "Other": "muted",
}

_sqlite_engine: Engine | None = None
_available_cache: bool | None = None


def _engine() -> Engine | None:
    """Return the engine to use for wallet queries."""
    global _sqlite_engine
    try:
        from purch import backend

        if backend.is_postgres():
            from purch.db_backend import get_engine

            return get_engine()
    except Exception as e:
        logging.exception(f"wallet engine lookup failed: {e}")

    if _sqlite_engine is not None:
        return _sqlite_engine
    try:
        from db.connection import DB_PATH

        _sqlite_engine = create_engine(f"sqlite:///{DB_PATH}", future=True)
        return _sqlite_engine
    except Exception as e:
        logging.exception(f"wallet sqlite fallback unavailable: {e}")
        return None


def available() -> bool:
    """True when the wallet tables are reachable on the active engine."""
    global _available_cache
    if _available_cache is not None:
        return _available_cache
    engine = _engine()
    if engine is None:
        _available_cache = False
        return False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT id FROM wallets LIMIT 1"))
        _available_cache = True
    except Exception as e:
        logging.exception(f"wallet tables unavailable: {e}")
        _available_cache = False
    return _available_cache


def _to_float(v: object) -> float:
    if v is None:
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def money(value: float) -> str:
    """Peso amount formatted for display (no currency symbol)."""
    return f"{value:,.2f}"


def _row_to_wallet(r: object) -> dict[str, str | int | float | bool]:
    return {
        "id": int(r[0]),
        "name": str(r[1] or ""),
        "wallet_type": str(r[2] or "Other"),
        "balance": _to_float(r[3]),
        "note": str(r[4] or ""),
        "is_archived": bool(r[5]),
    }


_SELECT_COLS = "id, name, wallet_type, balance, note, is_archived"


def list_wallets(user_id: str, include_archived: bool = False) -> list[dict]:
    """Return the user's wallets, active first, alphabetical by name."""
    engine = _engine()
    if engine is None or not user_id:
        return []
    sql = f"SELECT {_SELECT_COLS} FROM wallets WHERE user_id = :uid"
    if not include_archived:
        sql += " AND is_archived = :arch"
    sql += " ORDER BY name"
    params: dict[str, Any] = {"uid": user_id}
    if not include_archived:
        params["arch"] = False
    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).all()
    return [_row_to_wallet(r) for r in rows]


def get_wallet(user_id: str, wallet_id: int) -> dict | None:
    engine = _engine()
    if engine is None:
        return None
    with engine.connect() as conn:
        row = conn.execute(
            text(
                f"SELECT {_SELECT_COLS} FROM wallets "
                "WHERE id = :id AND user_id = :uid"
            ),
            {"id": int(wallet_id), "uid": user_id},
        ).first()
    return _row_to_wallet(row) if row else None


def create_wallet(
    user_id: str,
    name: str,
    wallet_type: str,
    balance: float,
    note: str = "",
) -> int:
    """Create a wallet and seed its opening ledger entry."""
    name = (name or "").strip()
    if not name:
        raise ValueError("Wallet nickname is required.")
    if wallet_type not in WALLET_TYPES:
        wallet_type = "Other"
    engine = _engine()
    if engine is None:
        raise RuntimeError("Wallet storage is unavailable.")
    now = datetime.utcnow()
    with engine.begin() as conn:
        dup = conn.execute(
            text(
                "SELECT id FROM wallets WHERE user_id = :uid AND name = :name"
            ),
            {"uid": user_id, "name": name},
        ).first()
        if dup:
            raise ValueError(f"You already have a wallet called “{name}”.")
        row = conn.execute(
            text(
                "INSERT INTO wallets "
                "(user_id, name, wallet_type, balance, starting_balance, "
                "note, is_archived, created_at, updated_at) VALUES "
                "(:uid, :name, :wtype, :bal, :bal, :note, :arch, :ts, :ts) "
                "RETURNING id"
            ),
            {
                "uid": user_id,
                "name": name,
                "wtype": wallet_type,
                "bal": float(balance or 0.0),
                "note": (note or "").strip() or None,
                "arch": False,
                "ts": now,
            },
        ).first()
        wallet_id = int(row[0])
        conn.execute(
            text(
                "INSERT INTO wallet_ledger "
                "(wallet_id, user_id, transaction_id, amount_delta, "
                "entry_type, description, created_at) VALUES "
                "(:wid, :uid, NULL, :delta, 'initial', :desc, :ts)"
            ),
            {
                "wid": wallet_id,
                "uid": user_id,
                "delta": float(balance or 0.0),
                "desc": "Opening balance",
                "ts": now,
            },
        )
    return wallet_id


def update_wallet(
    user_id: str,
    wallet_id: int,
    name: str,
    wallet_type: str,
    balance: float,
    note: str = "",
) -> None:
    """Rename / retype / re-note a wallet, and record any balance change
    as a `manual_adjustment` ledger entry."""
    name = (name or "").strip()
    if not name:
        raise ValueError("Wallet nickname is required.")
    if wallet_type not in WALLET_TYPES:
        wallet_type = "Other"
    engine = _engine()
    if engine is None:
        raise RuntimeError("Wallet storage is unavailable.")
    current = get_wallet(user_id, wallet_id)
    if current is None:
        raise ValueError("That wallet no longer exists.")
    now = datetime.utcnow()
    new_balance = float(balance or 0.0)
    delta = round(new_balance - current["balance"], 2)
    with engine.begin() as conn:
        dup = conn.execute(
            text(
                "SELECT id FROM wallets "
                "WHERE user_id = :uid AND name = :name AND id <> :id"
            ),
            {"uid": user_id, "name": name, "id": int(wallet_id)},
        ).first()
        if dup:
            raise ValueError(f"You already have a wallet called “{name}”.")
        conn.execute(
            text(
                "UPDATE wallets SET name = :name, wallet_type = :wtype, "
                "balance = :bal, note = :note, updated_at = :ts "
                "WHERE id = :id AND user_id = :uid"
            ),
            {
                "name": name,
                "wtype": wallet_type,
                "bal": new_balance,
                "note": (note or "").strip() or None,
                "ts": now,
                "id": int(wallet_id),
                "uid": user_id,
            },
        )
        if abs(delta) > 0.004:
            conn.execute(
                text(
                    "INSERT INTO wallet_ledger "
                    "(wallet_id, user_id, transaction_id, amount_delta, "
                    "entry_type, description, created_at) VALUES "
                    "(:wid, :uid, NULL, :delta, 'manual_adjustment', "
                    ":desc, :ts)"
                ),
                {
                    "wid": int(wallet_id),
                    "uid": user_id,
                    "delta": delta,
                    "desc": "Balance adjusted manually",
                    "ts": now,
                },
            )


def upsert_debt_wallet(
    user_id: str,
    name: str,
    wallet_type: str,
    amount: float,
    description: str = "",
) -> dict | None:
    """Create-or-increase a named Borrowed (`Debt`) / `Lent` wallet.

    Used by the chat debt/lent intent so "borrowed 250 from Aivann"
    actually persists: if a wallet nicknamed "Aivann" exists we add the
    amount to its balance (and un-archive it), otherwise we create it
    under the right type. Either way a ledger entry is written so the
    movement is auditable.

    Returns the wallet dict with an extra `created` flag, or None when
    the wallet tables aren't reachable.
    """
    amount = round(abs(float(amount or 0.0)), 2)
    if amount <= 0:
        return None
    if wallet_type not in WALLET_TYPES:
        wallet_type = "Other"
    engine = _engine()
    if engine is None or not user_id:
        return None

    clean_name = (name or "").strip()[:40] or (
        "Lent" if wallet_type == "Lent" else "Borrowed"
    )
    now = datetime.utcnow()
    created = False
    with engine.begin() as conn:
        existing = conn.execute(
            text(
                "SELECT id, balance, wallet_type FROM wallets "
                "WHERE user_id = :uid AND LOWER(name) = :name"
            ),
            {"uid": user_id, "name": clean_name.lower()},
        ).first()

        if existing is None:
            created = True
            row = conn.execute(
                text(
                    "INSERT INTO wallets "
                    "(user_id, name, wallet_type, balance, starting_balance, "
                    "note, is_archived, created_at, updated_at) VALUES "
                    "(:uid, :name, :wtype, :bal, :bal, :note, :arch, :ts, :ts) "
                    "RETURNING id"
                ),
                {
                    "uid": user_id,
                    "name": clean_name,
                    "wtype": wallet_type,
                    "bal": amount,
                    "note": (description or "").strip()[:120] or None,
                    "arch": False,
                    "ts": now,
                },
            ).first()
            if row is None:
                return None
            wallet_id = int(row[0])
            entry_type = "initial"
        else:
            wallet_id = int(existing[0])
            current_type = str(existing[2] or "Other")
            # Keep the existing type when it already belongs to the same
            # analytics group; otherwise realign it with the intent.
            new_type = (
                current_type
                if group_for(current_type) == group_for(wallet_type)
                else wallet_type
            )
            conn.execute(
                text(
                    "UPDATE wallets SET balance = balance + :amt, "
                    "wallet_type = :wtype, is_archived = :arch, "
                    "updated_at = :ts WHERE id = :id AND user_id = :uid"
                ),
                {
                    "amt": amount,
                    "wtype": new_type,
                    "arch": False,
                    "ts": now,
                    "id": wallet_id,
                    "uid": user_id,
                },
            )
            entry_type = "manual_adjustment"

        conn.execute(
            text(
                "INSERT INTO wallet_ledger "
                "(wallet_id, user_id, transaction_id, amount_delta, "
                "entry_type, description, created_at) VALUES "
                "(:wid, :uid, NULL, :delta, :etype, :desc, :ts)"
            ),
            {
                "wid": wallet_id,
                "uid": user_id,
                "delta": amount,
                "etype": entry_type,
                "desc": (description or "Wallet movement")[:180],
                "ts": now,
            },
        )

    wallet = get_wallet(user_id, wallet_id)
    if wallet is None:
        return None
    wallet["created"] = created
    return wallet


def delete_wallet(user_id: str, wallet_id: int) -> str | None:
    """Permanently remove a wallet and its ledger entries.

    Scoped to the owning user: both the ledger cleanup and the wallet row
    delete are filtered by `user_id`, so one account can never delete
    another's wallet. Ledger rows go first so the foreign key from
    `wallet_ledger.wallet_id` is never left dangling. Both statements run
    inside a single transaction, so a failure leaves the wallet intact.

    Returns the deleted wallet's nickname, or None when nothing matched.
    """
    engine = _engine()
    if engine is None:
        raise RuntimeError("Wallet storage is unavailable.")
    if not user_id or not wallet_id:
        return None
    with engine.begin() as conn:
        owned = conn.execute(
            text("SELECT name FROM wallets WHERE id = :id AND user_id = :uid"),
            {"id": int(wallet_id), "uid": user_id},
        ).first()
        if owned is None:
            return None
        name = str(owned[0] or "")
        conn.execute(
            text(
                "DELETE FROM wallet_ledger "
                "WHERE wallet_id = :id AND user_id = :uid"
            ),
            {"id": int(wallet_id), "uid": user_id},
        )
        conn.execute(
            text("DELETE FROM wallets WHERE id = :id AND user_id = :uid"),
            {"id": int(wallet_id), "uid": user_id},
        )
    return name


def set_archived(user_id: str, wallet_id: int, archived: bool) -> None:
    engine = _engine()
    if engine is None:
        raise RuntimeError("Wallet storage is unavailable.")
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE wallets SET is_archived = :arch, updated_at = :ts "
                "WHERE id = :id AND user_id = :uid"
            ),
            {
                "arch": bool(archived),
                "ts": datetime.utcnow(),
                "id": int(wallet_id),
                "uid": user_id,
            },
        )


def apply_purchase(
    user_id: str,
    wallet_id: int,
    amount: float,
    description: str,
    transaction_id: int | None = None,
) -> dict | None:
    """Subtract a purchase from a wallet and write the ledger entry.

    Returns the wallet dict (with its new balance) or None on failure.
    """
    amount = abs(float(amount or 0.0))
    if amount <= 0:
        return None
    engine = _engine()
    if engine is None:
        return None
    now = datetime.utcnow()
    with engine.begin() as conn:
        owned = conn.execute(
            text("SELECT id FROM wallets WHERE id = :id AND user_id = :uid"),
            {"id": int(wallet_id), "uid": user_id},
        ).first()
        if owned is None:
            return None
        conn.execute(
            text(
                "UPDATE wallets SET balance = balance - :amt, "
                "updated_at = :ts WHERE id = :id AND user_id = :uid"
            ),
            {
                "amt": amount,
                "ts": now,
                "id": int(wallet_id),
                "uid": user_id,
            },
        )
        conn.execute(
            text(
                "INSERT INTO wallet_ledger "
                "(wallet_id, user_id, transaction_id, amount_delta, "
                "entry_type, description, created_at) VALUES "
                "(:wid, :uid, :txid, :delta, 'purchase', :desc, :ts)"
            ),
            {
                "wid": int(wallet_id),
                "uid": user_id,
                "txid": int(transaction_id) if transaction_id else None,
                "delta": -amount,
                "desc": (description or "Purchase")[:180],
                "ts": now,
            },
        )
    return get_wallet(user_id, wallet_id)


def recent_ledger(user_id: str, wallet_id: int, limit: int = 5) -> list[dict]:
    """Recent movements for one wallet — used by the wallets page."""
    engine = _engine()
    if engine is None:
        return []
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT amount_delta, entry_type, description, created_at "
                "FROM wallet_ledger "
                "WHERE user_id = :uid AND wallet_id = :wid "
                "ORDER BY id DESC LIMIT :lim"
            ),
            {"uid": user_id, "wid": int(wallet_id), "lim": int(limit)},
        ).all()
    out: list[dict] = []
    for r in rows:
        out.append(
            {
                "delta": _to_float(r[0]),
                "entry_type": str(r[1] or ""),
                "description": str(r[2] or ""),
            }
        )
    return out


def match_wallet(wallets: list[dict], hint: str) -> dict | None:
    """Resolve a free-text hint onto one of the user's wallets.

    Ordered strategy: exact name → name contained in the hint (or vice
    versa) → wallet-type keyword → fuzzy ratio. Deliberately forgiving
    about misspellings, but the UI always offers explicit buttons so a
    bad guess is never the only path.
    """
    hint = (hint or "").strip().lower()
    if not hint or not wallets:
        return None

    for w in wallets:
        if w["name"].lower() == hint:
            return w
    for w in wallets:
        name = w["name"].lower()
        if name and (name in hint or hint in name):
            return w

    for wtype, keywords in TYPE_KEYWORDS.items():
        if any(k in hint for k in keywords):
            for w in wallets:
                if w["wallet_type"] == wtype:
                    return w

    names = [w["name"].lower() for w in wallets]
    close = difflib.get_close_matches(hint, names, n=1, cutoff=0.6)
    if close:
        for w in wallets:
            if w["name"].lower() == close[0]:
                return w
    return None


def detect_wallet_in_text(wallets: list[dict], message: str) -> dict | None:
    """Scan a raw chat message for a wallet reference without an LLM."""
    low = (message or "").lower()
    if not low or not wallets:
        return None
    for w in wallets:
        name = w["name"].lower()
        if name and name in low:
            return w
    for wtype, keywords in TYPE_KEYWORDS.items():
        if any(k in low for k in keywords):
            for w in wallets:
                if w["wallet_type"] == wtype:
                    return w
    return None


def group_for(wallet_type: str) -> str:
    """Return the analytics group a wallet type belongs to."""
    for group, types in WALLET_GROUPS.items():
        if wallet_type in types:
            return group
    return "Debit"


def consumable_wallets(wallets: list[dict]) -> list[dict]:
    """Wallets that can actually be spent from (Cash / Bank only)."""
    return [w for w in wallets if w["wallet_type"] in CONSUMABLE_TYPES]


def consumable_total(wallets: list[dict]) -> float:
    return sum(float(w["balance"]) for w in consumable_wallets(wallets))


def summary(wallets: list[dict]) -> dict[str, float]:
    """Aggregate totals for the wallets page header."""
    assets = sum(
        w["balance"]
        for w in wallets
        if w["wallet_type"] in ("Cash", "Bank", "Savings", "Lent", "Other")
    )
    liabilities = sum(
        w["balance"] for w in wallets if w["wallet_type"] in ("Debt", "Loan")
    )
    return {
        "assets": assets,
        "liabilities": liabilities,
        "net": assets - liabilities,
    }
