"""Database models — PostgreSQL-compatible (uses get_engine + text)."""

from sqlalchemy import text


def _get_engine():
    from app.services.db_backend import get_engine
    return get_engine()


# ── Budgets ───────────────────────────────────────────────────────────

def set_budget(user_id: str, category: str, limit_amount: float, period: str = "monthly"):
    if limit_amount <= 0:
        raise ValueError("limit_amount must be positive")
    engine = _get_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO budgets (user_id, category, limit_amount, period) "
                "VALUES (:uid, :cat, :limit, :period) "
                "ON CONFLICT (user_id, category, period) DO UPDATE SET limit_amount = EXCLUDED.limit_amount"
            ),
            {"uid": user_id, "cat": category, "limit": limit_amount, "period": period},
        )


def zero_budget(user_id: str, category: str, period: str = "monthly"):
    """Sets a budget's limit to 0 while keeping the row."""
    engine = _get_engine()
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "INSERT INTO budgets (user_id, category, limit_amount, period) "
                "VALUES (:uid, :cat, 0, :period) "
                "ON CONFLICT (user_id, category, period) DO UPDATE SET limit_amount = 0 RETURNING id"
            ),
            {"uid": user_id, "cat": category, "period": period},
        )
        return result.scalar()


def delete_budget(user_id: str, category: str, period: str = "monthly") -> bool:
    """Deletes a budget row. Returns True if a row was actually deleted."""
    engine = _get_engine()
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "DELETE FROM budgets WHERE user_id = :uid AND category = :cat AND period = :period"
            ),
            {"uid": user_id, "cat": category, "period": period},
        )
        return result.rowcount > 0


def get_budget(user_id: str, category: str, period: str = "monthly"):
    """Returns the budget limit_amount, or None if not set."""
    engine = _get_engine()
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT limit_amount FROM budgets WHERE user_id = :uid AND category = :cat AND period = :period"
            ),
            {"uid": user_id, "cat": category, "period": period},
        ).fetchone()
        return row[0] if row else None


def get_user_categories(user_id: str) -> list[str]:
    """Distinct categories this user actually uses, from budgets and transactions."""
    engine = _get_engine()
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                "SELECT category FROM budgets WHERE user_id = :uid "
                "UNION "
                "SELECT category FROM transactions WHERE user_id = :uid"
            ),
            {"uid": user_id},
        ).fetchall()
        return [row[0] for row in rows if row[0]]


# ── Transactions ──────────────────────────────────────────────────────

def insert_transaction(user_id: str, raw_text: str, item: str, amount: float,
                       category: str, tx_date: str = None, wallet: str = None) -> int:
    if amount <= 0:
        raise ValueError(f"amount must be positive, got {amount}")
    if not item or not category:
        raise ValueError("item and category cannot be empty")

    engine = _get_engine()
    with engine.begin() as conn:
        if tx_date:
            result = conn.execute(
                text(
                    "INSERT INTO transactions (user_id, raw_text, item, amount, category, wallet, tx_timestamp) "
                    "VALUES (:uid, :raw, :item, :amount, :cat, :wallet, :ts) RETURNING id"
                ),
                {"uid": user_id, "raw": raw_text, "item": item, "amount": amount,
                 "cat": category, "wallet": wallet or "", "ts": f"{tx_date} 12:00:00"},
            )
        else:
            result = conn.execute(
                text(
                    "INSERT INTO transactions (user_id, raw_text, item, amount, category, wallet) "
                    "VALUES (:uid, :raw, :item, :amount, :cat, :wallet) RETURNING id"
                ),
                {"uid": user_id, "raw": raw_text, "item": item, "amount": amount,
                 "cat": category, "wallet": wallet or ""},
            )
        return result.scalar()


def get_recent_transactions(user_id: str, limit: int = 10):
    """Returns the most recent transactions, newest first."""
    engine = _get_engine()
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                "SELECT id, item, amount, category, tx_timestamp "
                "FROM transactions WHERE user_id = :uid "
                "ORDER BY tx_timestamp DESC LIMIT :limit"
            ),
            {"uid": user_id, "limit": limit},
        ).fetchall()
        return [dict(row._mapping) for row in rows]


def query_transactions(user_id: str, category: str = None, category_mode: str = "include",
                       start_date: str = None, end_date: str = None, limit: int = None,
                       item_hint: str = None):
    engine = _get_engine()
    with engine.begin() as conn:
        query = "SELECT item, amount, category, tx_timestamp FROM transactions WHERE user_id = :uid"
        params = {"uid": user_id}

        if item_hint:
            query += " AND item LIKE :item_hint"
            params["item_hint"] = f"%{item_hint}%"
        if category:
            if category_mode == "exclude":
                query += " AND category != :category"
            else:
                query += " AND category = :category"
            params["category"] = category
        if start_date:
            query += " AND tx_timestamp >= :start_date"
            params["start_date"] = f"{start_date} 00:00:00"
        if end_date:
            query += " AND tx_timestamp <= :end_date"
            params["end_date"] = f"{end_date} 23:59:59"
        query += " ORDER BY tx_timestamp DESC"
        if limit:
            query += " LIMIT :limit"
            params["limit"] = limit

        rows = conn.execute(text(query), params).fetchall()
        return [dict(row._mapping) for row in rows]


def update_transaction(user_id: str, tx_id: int, **fields) -> bool:
    """Update specific fields of a transaction. Returns True if updated."""
    allowed = {"item", "amount", "category"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return False

    engine = _get_engine()
    with engine.begin() as conn:
        set_clause = ", ".join(f"{k} = :{k}" for k in updates)
        params = {"uid": user_id, "id": tx_id, **updates}
        result = conn.execute(
            text(f"UPDATE transactions SET {set_clause} WHERE id = :id AND user_id = :uid"),
            params,
        )
        return result.rowcount > 0


def delete_transaction(user_id: str, tx_id: int) -> bool:
    engine = _get_engine()
    with engine.begin() as conn:
        result = conn.execute(
            text("DELETE FROM transactions WHERE id = :id AND user_id = :uid"),
            {"id": tx_id, "uid": user_id},
        )
        return result.rowcount > 0


# ── User tone ─────────────────────────────────────────────────────────

def get_user_tone(user_id: str) -> str:
    """Returns the user's tone preference, defaulting to 'neutral'."""
    engine = _get_engine()
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT tone_pref FROM users WHERE id = :uid"),
            {"uid": user_id},
        ).fetchone()
        return row[0] if row else "neutral"


def set_user_tone(user_id: str, tone: str):
    engine = _get_engine()
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE users SET tone_pref = :tone WHERE id = :uid"),
            {"tone": tone, "uid": user_id},
        )


# ── Spending helpers ──────────────────────────────────────────────────

def get_month_spent(user_id: str, category: str) -> float:
    """Total spent this calendar month for a category."""
    engine = _get_engine()
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT COALESCE(SUM(amount), 0) FROM transactions "
                "WHERE user_id = :uid AND category = :cat "
                "AND tx_timestamp >= date_trunc('month', now())"
            ),
            {"uid": user_id, "cat": category},
        ).fetchone()
        return float(row[0]) if row else 0.0


# ── Transaction search ───────────────────────────────────────────────

def find_best_match_transaction(user_id: str, item_hint: str, limit: int = 5):
    """Find transactions matching item_hint (fuzzy LIKE)."""
    engine = _get_engine()
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                "SELECT id, item, amount, category, tx_timestamp "
                "FROM transactions WHERE user_id = :uid "
                "AND item ILIKE :hint "
                "ORDER BY tx_timestamp DESC LIMIT :limit"
            ),
            {"uid": user_id, "hint": f"%{item_hint}%", "limit": limit},
        ).fetchall()
        return [dict(row._mapping) for row in rows]


# ── Interaction log ──────────────────────────────────────────────────

def log_interaction(user_id: str, prompt: str, response: str, intent: str = "chat"):
    """Log a user-assistant interaction."""
    engine = _get_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO interaction_log (user_id, prompt, response, intent) "
                "VALUES (:uid, :prompt, :response, :intent)"
            ),
            {"uid": user_id, "prompt": prompt, "response": response, "intent": intent},
        )
