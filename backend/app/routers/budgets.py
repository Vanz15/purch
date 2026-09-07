"""Budgets API — CRUD for user-defined budgets.

Users can manually add, edit, and delete budgets. Each budget ties a
category name to a spending limit. The analytics endpoint already
joins budgets with transactions to compute spent/remaining.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.deps import get_current_user_id
from app.services.db_backend import get_engine
from app.routers.analytics import _cache, _cache_times
from sqlalchemy import text

logger = logging.getLogger("purch.budgets")


def _invalidate_analytics_cache(user_id: str):
    stale_keys = [k for k in _cache if k[0] == user_id]
    for k in stale_keys:
        _cache.pop(k, None)
        _cache_times.pop(k, None)


router = APIRouter(prefix="/api/budgets", tags=["budgets"])


class BudgetCreate(BaseModel):
    category: str
    limit_amount: float
    period: str = "monthly"


class BudgetUpdate(BaseModel):
    category: str | None = None
    limit_amount: float | None = None


class BudgetOut(BaseModel):
    id: int
    category: str
    limit_amount: float
    period: str


# ── List ──────────────────────────────────────────────────────────────
@router.get("")
async def list_budgets(user_id: str = Depends(get_current_user_id)):
    engine = get_engine()
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                "SELECT id, category, limit_amount, period "
                "FROM budgets WHERE user_id = :uid ORDER BY category"
            ),
            {"uid": user_id},
        ).fetchall()
    return [BudgetOut(id=r[0], category=r[1], limit_amount=r[2], period=r[3]) for r in rows]


# ── Create ────────────────────────────────────────────────────────────
@router.post("")
async def create_budget(body: BudgetCreate, user_id: str = Depends(get_current_user_id)):
    if not body.category.strip():
        raise HTTPException(400, "Category name is required")
    if body.limit_amount <= 0:
        raise HTTPException(400, "Limit must be greater than 0")

    engine = get_engine()
    with engine.begin() as conn:
        # Check for duplicate
        existing = conn.execute(
            text(
                "SELECT id FROM budgets WHERE user_id = :uid AND category = :cat AND period = :period"
            ),
            {"uid": user_id, "cat": body.category.strip(), "period": body.period},
        ).fetchone()
        if existing:
            raise HTTPException(409, f"A budget for '{body.category.strip()}' already exists")

        result = conn.execute(
            text(
                "INSERT INTO budgets (user_id, category, limit_amount, period) "
                "VALUES (:uid, :cat, :limit, :period) RETURNING id"
            ),
            {"uid": user_id, "cat": body.category.strip(), "limit": body.limit_amount, "period": body.period},
        )
        new_id = result.scalar()

    _invalidate_analytics_cache(user_id)
    return BudgetOut(id=new_id, category=body.category.strip(), limit_amount=body.limit_amount, period=body.period)


# ── Update ────────────────────────────────────────────────────────────
@router.put("/{budget_id}")
async def update_budget(budget_id: int, body: BudgetUpdate, user_id: str = Depends(get_current_user_id)):
    engine = get_engine()
    with engine.begin() as conn:
        existing = conn.execute(
            text(
                "SELECT id, category, limit_amount, period FROM budgets WHERE id = :id AND user_id = :uid"
            ),
            {"id": budget_id, "uid": user_id},
        ).fetchone()
        if not existing:
            raise HTTPException(404, "Budget not found")

        new_cat = body.category.strip() if body.category else existing[1]
        new_limit = body.limit_amount if body.limit_amount is not None else existing[2]

        if new_limit <= 0:
            raise HTTPException(400, "Limit must be greater than 0")

        # Check duplicate if category changed
        if body.category and body.category.strip() != existing[1]:
            dup = conn.execute(
                text(
                    "SELECT id FROM budgets WHERE user_id = :uid AND category = :cat AND period = :period AND id != :id"
                ),
                {"uid": user_id, "cat": new_cat, "period": existing[3], "id": budget_id},
            ).fetchone()
            if dup:
                raise HTTPException(409, f"A budget for '{new_cat}' already exists")

        conn.execute(
            text(
                "UPDATE budgets SET category = :cat, limit_amount = :limit WHERE id = :id"
            ),
            {"cat": new_cat, "limit": new_limit, "id": budget_id},
        )

    _invalidate_analytics_cache(user_id)
    return BudgetOut(id=budget_id, category=new_cat, limit_amount=new_limit, period=existing[3])


# ── Delete ────────────────────────────────────────────────────────────
@router.delete("/{budget_id}")
async def delete_budget(budget_id: int, user_id: str = Depends(get_current_user_id)):
    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "DELETE FROM budgets WHERE id = :id AND user_id = :uid"
            ),
            {"id": budget_id, "uid": user_id},
        )
        if result.rowcount == 0:
            raise HTTPException(404, "Budget not found")

    _invalidate_analytics_cache(user_id)
    return {"ok": True}
