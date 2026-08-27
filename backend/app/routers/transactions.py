"""Transactions API — list with category filter + free-text search.

Read-only. Mirrors the spending-log view from the old AnalyticsState.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text

from app.deps import get_current_user_id
from app.services import bootstrap as backend
from app.services.db_backend import get_engine

logger = logging.getLogger("purch.transactions")

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


class TransactionRow(BaseModel):
    transaction_id: int | None = None
    item: str = ""
    amount: float = 0.0
    amount_display: str = ""
    category: str = ""
    tx_timestamp: str = ""
    wallet: str = ""


@router.get("")
async def list_transactions(
    category: str | None = Query(None, description="Exact category filter"),
    q: str | None = Query(None, description="Free-text search on item/category"),
    limit: int = Query(200, ge=1, le=1000),
    user_id: str = Depends(get_current_user_id),
):
    if not backend.is_postgres():
        raise HTTPException(status_code=503, detail="Transaction storage is unavailable right now.")

    engine = get_engine()
    clauses = ["user_id = :uid"]
    params: dict = {"uid": user_id, "lim": limit}
    if category:
        clauses.append("category = :cat")
        params["cat"] = category
    if q:
        clauses.append("(item ILIKE :q OR category ILIKE :q)")
        params["q"] = f"%{q}%"

    where = " AND ".join(clauses)
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"SELECT id, item, amount, category, tx_timestamp "
                    f"FROM transactions WHERE {where} "
                    f"ORDER BY tx_timestamp DESC LIMIT :lim"
                ),
                params,
            ).all()
            # Distinct categories for the filter dropdown.
            cats = conn.execute(
                text(
                    "SELECT DISTINCT category FROM transactions "
                    "WHERE user_id = :uid ORDER BY category"
                ),
                {"uid": user_id},
            ).all()
    except Exception as e:  # pragma: no cover - defensive
        logger.exception(f"transaction list failed: {e}")
        raise HTTPException(status_code=500, detail="Could not load transactions.")

    def _fmt(v) -> str:
        if v is None:
            return ""
        if hasattr(v, "strftime"):
            return (v + __import__("datetime").timedelta(hours=8)).strftime("%Y-%m-%d %H:%M")
        try:
            return str(v)
        except Exception:
            return str(v)

    out = []
    for r in rows:
        amt = float(r[2] or 0)
        out.append(
            TransactionRow(
                transaction_id=int(r[0]) if r[0] is not None else None,
                item=str(r[1] or ""),
                amount=amt,
                amount_display=backend.money(amt) if hasattr(backend, "money") else f"₱{amt:.2f}",
                category=str(r[3] or ""),
                tx_timestamp=_fmt(r[4]),
                wallet=str(r[5]) if len(r) > 5 else "",
            )
        )
    return {
        "transactions": out,
        "categories": [str(c[0]) for c in cats],
        "total": len(out),
    }


class TransactionUpdate(BaseModel):
    item: str | None = None
    amount: float | None = None
    category: str | None = None


@router.put("/{transaction_id}")
async def update_transaction(
    transaction_id: int,
    body: TransactionUpdate,
    user_id: str = Depends(get_current_user_id),
):
    """Edit a transaction's item / amount / category. Ownership is enforced
    by the user_id scoping inside pg_update_transaction."""
    if not backend.is_postgres():
        raise HTTPException(status_code=503, detail="Transaction storage is unavailable right now.")
    try:
        backend.update_transaction(
            tx_id=transaction_id,
            item=body.item,
            amount=body.amount,
            category=body.category,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # pragma: no cover - defensive
        logger.exception(f"transaction update failed: {e}")
        raise HTTPException(status_code=500, detail="Could not update transaction.")
    return {"ok": True}


@router.delete("/{transaction_id}")
async def delete_transaction(
    transaction_id: int,
    user_id: str = Depends(get_current_user_id),
):
    if not backend.is_postgres():
        raise HTTPException(status_code=503, detail="Transaction storage is unavailable right now.")
    try:
        backend.delete_transaction(tx_id=transaction_id)
    except Exception as e:  # pragma: no cover - defensive
        logger.exception(f"transaction delete failed: {e}")
        raise HTTPException(status_code=500, detail="Could not delete transaction.")
    return {"ok": True}
