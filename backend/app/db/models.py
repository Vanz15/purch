import sqlite3
from db.connection import get_connection


def insert_transaction(user_id: str, raw_text: str, item: str, amount: float, category: str, tx_date: str = None) -> int:
    if amount <= 0:
        raise ValueError(f"amount must be positive, got {amount}")
    if not item or not category:
        raise ValueError("item and category cannot be empty")

    conn = get_connection()
    try:
        if tx_date:
            cur = conn.execute(
                """
                INSERT INTO transactions (user_id, raw_text, item, amount, category, tx_timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, raw_text, item, amount, category, f"{tx_date} 12:00:00"),
            )
        else:
            cur = conn.execute(
                """
                INSERT INTO transactions (user_id, raw_text, item, amount, category)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, raw_text, item, amount, category),
            )
        conn.commit()
        return cur.lastrowid
    except sqlite3.Error as e:
        conn.rollback()
        raise RuntimeError(f"Failed to insert transaction: {e}") from e
    finally:
        conn.close()

def get_recent_transactions(user_id: str, limit: int = 10):
    """Returns the most recent transactions for a user, newest first."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, item, amount, category, tx_timestamp
            FROM transactions
            WHERE user_id = ?
            ORDER BY tx_timestamp DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
        transactions = [dict(row) for row in rows]
        for t in transactions:
            t["tx_timestamp"] = to_local_time_str(t["tx_timestamp"])
        return transactions
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to fetch transactions: {e}") from e
    finally:
        conn.close()

def get_user_tone(user_id: str) -> str:
    """Returns the user's tone preference, defaulting to 'neutral'."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT tone_pref FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        return row["tone_pref"] if row else "neutral"
    finally:
        conn.close()


def set_user_tone(user_id: str, tone: str):
    """Updates the user's tone preference."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE users SET tone_pref = ? WHERE id = ?", (tone, user_id)
        )
        conn.commit()
    finally:
        conn.close()

def query_transactions(user_id: str, category: str = None, category_mode: str = "include",
                        start_date: str = None, end_date: str = None, limit: int = None,
                        item_hint: str = None):
    conn = get_connection()
    try:
        query = "SELECT item, amount, category, tx_timestamp FROM transactions WHERE user_id = ?"
        params = [user_id]

        if item_hint:
            query += " AND item LIKE ?"
            params.append(f"%{item_hint}%")
        if category:
            if category_mode == "exclude":
                query += " AND category != ?"
            else:
                query += " AND category = ?"
            params.append(category)
        if start_date:
            query += " AND date(tx_timestamp) >= date(?)"
            params.append(start_date)
        if end_date:
            query += " AND date(tx_timestamp) <= date(?)"
            params.append(end_date)

        query += " ORDER BY tx_timestamp DESC"
        if limit:
            query += " LIMIT ?"
            params.append(limit)

        rows = conn.execute(query, params).fetchall()
        transactions = [dict(row) for row in rows]
        for t in transactions:
            t["tx_timestamp"] = to_local_time_str(t["tx_timestamp"])
        total = sum(t["amount"] for t in transactions)
        return {"transactions": transactions, "total": total, "count": len(transactions)}
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to query transactions: {e}") from e
    finally:
        conn.close()

def set_budget(user_id: str, category: str, limit_amount: float, period: str = "monthly"):
    if limit_amount <= 0:
        raise ValueError("limit_amount must be positive")
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO budgets (user_id, category, limit_amount, period)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, category, period)
            DO UPDATE SET limit_amount = excluded.limit_amount
            """,
            (user_id, category, limit_amount, period),
        )
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise RuntimeError(f"Failed to set budget: {e}") from e
    finally:
        conn.close()


def get_budget(user_id: str, category: str, period: str = "monthly"):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT limit_amount FROM budgets WHERE user_id=? AND category=? AND period=?",
            (user_id, category, period),
        ).fetchone()
        return row["limit_amount"] if row else None
    finally:
        conn.close()


def get_month_spent(user_id: str, category: str):
    """Total spent in the given category so far this calendar month."""
    from datetime import date
    start_of_month = date.today().replace(day=1).isoformat()
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(amount), 0) as total FROM transactions
            WHERE user_id=? AND category=? AND date(tx_timestamp) >= date(?)
            """,
            (user_id, category, start_of_month),
        ).fetchone()
        return row["total"]
    finally:
        conn.close()

def get_transaction_by_id(tx_id: int):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, item, amount, category, tx_timestamp FROM transactions WHERE id = ?",
            (tx_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def find_best_match_transaction(user_id: str, item_hint: str = None, limit: int = 5):
    """Returns recent transactions, optionally filtered by an item keyword,
    for resolving which transaction an edit message refers to."""
    conn = get_connection()
    try:
        query = "SELECT id, item, amount, category, tx_timestamp FROM transactions WHERE user_id = ?"
        params = [user_id]
        if item_hint:
            query += " AND item LIKE ?"
            params.append(f"%{item_hint}%")
        query += " ORDER BY tx_timestamp DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        transactions = [dict(row) for row in rows]
        for t in transactions:
            t["tx_timestamp"] = to_local_time_str(t["tx_timestamp"])
        return transactions
    finally:
        conn.close()


def update_transaction(tx_id: int, item: str = None, amount: float = None, category: str = None):
    if amount is not None and amount <= 0:
        raise ValueError("amount must be positive")
    conn = get_connection()
    try:
        fields, params = [], []
        if item is not None:
            fields.append("item = ?"); params.append(item)
        if amount is not None:
            fields.append("amount = ?"); params.append(amount)
        if category is not None:
            fields.append("category = ?"); params.append(category)
        if not fields:
            return
        params.append(tx_id)
        conn.execute(f"UPDATE transactions SET {', '.join(fields)} WHERE id = ?", params)
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise RuntimeError(f"Failed to update transaction: {e}") from e
    finally:
        conn.close()

def log_interaction(user_id: str, raw_message: str, intent: str, extracted: dict, response: str):
    """Best-effort logging — never let a logging failure break the app."""
    import json as json_module
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO interaction_log (user_id, raw_message, intent, extracted_json, response) VALUES (?, ?, ?, ?, ?)",
            (user_id, raw_message, intent, json_module.dumps(extracted) if extracted else None, response),
        )
        conn.commit()
    except Exception:
        pass  # logging must never crash the main flow
    finally:
        conn.close()

def delete_transaction(tx_id: int):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise RuntimeError(f"Failed to delete transaction: {e}") from e
    finally:
        conn.close()

from datetime import timedelta

PH_OFFSET = timedelta(hours=8)  # Philippines is UTC+8

def to_local_time_str(dt_or_str):
    """Converts a stored UTC timestamp to a PH-local display string."""
    from datetime import datetime
    if isinstance(dt_or_str, str):
        dt = datetime.strptime(dt_or_str, "%Y-%m-%d %H:%M:%S")
    else:
        dt = dt_or_str
    local_dt = dt + PH_OFFSET
    return local_dt.strftime("%Y-%m-%d %H:%M")

def get_all_budgets_and_spending(user_id: str, categories: list):
    """Single pass: returns {category: {limit, spent}} for every category."""
    from datetime import date
    start_of_month = date.today().replace(day=1).isoformat()

    conn = get_connection()
    try:
        budget_rows = {}
        for row in conn.execute(
            "SELECT category, limit_amount FROM budgets WHERE user_id = ? AND period = 'monthly'",
            (user_id,),
        ).fetchall():
            budget_rows[row["category"]] = row["limit_amount"]

        spent_rows = {}
        for row in conn.execute(
            """
            SELECT category, COALESCE(SUM(amount), 0) as total
            FROM transactions
            WHERE user_id = ? AND date(tx_timestamp) >= date(?)
            GROUP BY category
            """,
            (user_id, start_of_month),
        ).fetchall():
            spent_rows[row["category"]] = row["total"]

        return {
            cat: {"limit": budget_rows.get(cat), "spent": spent_rows.get(cat, 0.0)}
            for cat in categories
        }
    finally:
        conn.close()