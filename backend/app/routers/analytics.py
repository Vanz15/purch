"""Analytics API — ports AnalyticsState.refresh to HTTP.

SQL-first and mostly framework-independent already. year=0/month=0 means
"current calendar month" (matches old selected_year/selected_month == 0).
Postgres-only: when backend.is_postgres() is False we return
unavailable=True and skip the queries (SQLite date_trunc/INTERVAL aren't portable).
"""
import logging
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text

from app.deps import get_current_user_id
from app.services import bootstrap as backend
from app.services.time_utils import today_in_timezone

logger = logging.getLogger("purch.analytics")

# --- Simple in-memory TTL cache for the heavy analytics query ---
# Repeated loads (sidebar refresh, page mount, toggles) hit the cache
# instead of re-running 5 sequential Postgres round-trips.
_ANALYTICS_TTL = 5.0  # seconds
_cache: dict = {}
_cache_times: dict = {}


def _cached_analytics(user_id: str, year: int, month: int, builder):
    key = (user_id, year, month)
    now = datetime.now()
    if key in _cache and (now - _cache_times[key]).total_seconds() < _ANALYTICS_TTL:
        logger.info("analytics cache HIT for %s", key)
        return _cache[key]
    logger.info("analytics cache MISS for %s", key)
    result = builder()
    _cache[key] = result
    _cache_times[key] = now
    return result


router = APIRouter(prefix="/api/analytics", tags=["analytics"])

_RECENT_LIMIT = 10
_MIN_YEAR = 2000


class KpiSnapshot(BaseModel):
    tx_count: int = 0
    total: float = 0.0


class CategoryRow(BaseModel):
    category: str
    total: float
    count: int
    pct_of_total: int


class TrendPoint(BaseModel):
    day: str
    iso: str
    total: float
    count: int


class BudgetStatusRow(BaseModel):
    category: str
    limit_amount: float
    spent: float
    pct: int
    remaining: float
    status: str


class RecentTx(BaseModel):
    item: str
    amount: float
    category: str
    tx_timestamp: str


def _to_float(v) -> float:
    if v is None:
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _to_int(v) -> int:
    if v is None:
        return 0
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _format_ts(v) -> str:
    if v is None:
        return ""
    if isinstance(v, datetime):
        dt = v
    else:
        try:
            dt = datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            try:
                dt = datetime.fromisoformat(v)
            except ValueError:
                return str(v)
    return (dt + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M")


def _add_months(start: date, delta: int) -> date:
    total = (start.year * 12) + (start.month - 1) + delta
    return date(total // 12, (total % 12) + 1, 1)


@router.get("")
async def get_analytics(year: int = 0, month: int = 0, user_id: str = Depends(get_current_user_id)):
    if not backend.is_postgres():
        return {
            "kpi": {"tx_count": 0, "total": 0.0},
            "categories": [],
            "trend": [],
            "budgets": [],
            "recent": [],
            "unavailable": True,
        }

    from app.services.db_backend import get_engine

    try:
        engine = get_engine()
    except Exception as e:
        logger.exception(f"engine lookup failed: {e}")
        return {
            "kpi": {"tx_count": 0, "total": 0.0},
            "categories": [],
            "trend": [],
            "budgets": [],
            "recent": [],
            "unavailable": True,
        }

    today = today_in_timezone("")
    current_month = today.replace(day=1)
    if year and month:
        try:
            month_start = date(year, month, 1)
        except ValueError:
            month_start = current_month
    else:
        month_start = current_month
    if month_start > current_month:
        month_start = current_month
    month_end = _add_months(month_start, 1)
    trend_end = today if month_start == current_month else month_end - timedelta(days=1)
    window = {
        "uid": user_id,
        "month_start": month_start.isoformat(),
        "month_end": month_end.isoformat(),
    }

    def _run_queries():
        with engine.connect() as conn:
            kpi_row = conn.execute(
                text(
                    "SELECT COUNT(*) AS tx_count, COALESCE(SUM(amount), 0) AS total "
                    "FROM transactions "
                    "WHERE user_id = :uid "
                    "AND tx_timestamp >= (:month_start)::timestamp "
                    "AND tx_timestamp < (:month_end)::timestamp"
                ),
                window,
            ).first()

            cat_rows = conn.execute(
                text(
                    "SELECT category, COALESCE(SUM(amount), 0) AS total, COUNT(*) AS cnt "
                    "FROM transactions WHERE user_id = :uid "
                    "AND tx_timestamp >= (:month_start)::timestamp "
                    "AND tx_timestamp < (:month_end)::timestamp "
                    "GROUP BY category ORDER BY total DESC"
                ),
                window,
            ).all()

            trend_rows = conn.execute(
                text(
                    "SELECT CAST(tx_timestamp AS DATE) AS day, COALESCE(SUM(amount), 0) AS total, "
                    "COUNT(*) AS cnt FROM transactions WHERE user_id = :uid "
                    "AND tx_timestamp >= (:month_start)::timestamp "
                    "AND tx_timestamp < (:month_end)::timestamp "
                    "GROUP BY CAST(tx_timestamp AS DATE) ORDER BY day"
                ),
                window,
            ).all()

            budget_rows = conn.execute(
                text(
                    "SELECT b.category, b.limit_amount, COALESCE(SUM(t.amount), 0) AS spent "
                    "FROM budgets b LEFT JOIN transactions t "
                    "ON t.user_id = b.user_id AND t.category = b.category "
                    "AND t.tx_timestamp >= (:month_start)::timestamp "
                    "AND t.tx_timestamp < (:month_end)::timestamp "
                    "WHERE b.user_id = :uid AND b.period = 'monthly' "
                    "GROUP BY b.category, b.limit_amount ORDER BY b.category"
                ),
                window,
            ).all()

            recent_rows = conn.execute(
                text(
                    "SELECT item, amount, category, tx_timestamp FROM transactions "
                    "WHERE user_id = :uid "
                    "AND tx_timestamp >= (:month_start)::timestamp "
                    "AND tx_timestamp < (:month_end)::timestamp "
                    "ORDER BY tx_timestamp DESC LIMIT :lim"
                ),
                {**window, "lim": _RECENT_LIMIT},
            ).all()
        return kpi_row, cat_rows, trend_rows, budget_rows, recent_rows

    kpi_row, cat_rows, trend_rows, budget_rows, recent_rows = _cached_analytics(
        user_id, year, month, _run_queries
    )

    # ---- KPIs ----
    month_tx_count = _to_int(kpi_row[0]) if kpi_row else 0
    month_spent = _to_float(kpi_row[1]) if kpi_row else 0.0

    # ---- Categories ----
    categories = []
    for r in cat_rows:
        total = _to_float(r[1])
        pct = int(round((total / month_spent) * 100)) if month_spent else 0
        categories.append(CategoryRow(category=str(r[0]), total=total, count=_to_int(r[2]), pct_of_total=pct))
    top_category = categories[0].category if categories else "—"
    top_category_amount = categories[0].total if categories else 0.0

    # ---- Trend (densify to daily) ----
    trend_by_day = {str(r[0]): (r[1], r[2]) for r in trend_rows}
    trend: list[TrendPoint] = []
    d = month_start
    while d <= trend_end:
        total, cnt = trend_by_day.get(str(d), (0.0, 0))
        trend.append(TrendPoint(day=d.strftime("%b %d"), iso=d.isoformat(), total=_to_float(total), count=_to_int(cnt)))
        d += timedelta(days=1)
    trend_peak = max((p.total for p in trend), default=0.0)

    # ---- Budgets ----
    budgets = []
    budget_limit_total = 0.0
    budget_spent_total = 0.0
    for r in budget_rows:
        limit_amt = _to_float(r[1])
        spent = _to_float(r[2])
        pct = int(round((spent / limit_amt) * 100)) if limit_amt else 0
        status = "over" if pct >= 100 else ("near" if pct >= 80 else "on_track")
        budgets.append(BudgetStatusRow(
            category=str(r[0]), limit_amount=limit_amt, spent=spent,
            pct=min(pct, 150), remaining=limit_amt - spent, status=status,
        ))
        budget_limit_total += limit_amt
        budget_spent_total += spent
    budget_used_pct = int(round((budget_spent_total / budget_limit_total) * 100)) if budget_limit_total else 0

    # ---- Recent ----
    recent = [
        RecentTx(item=str(r[0]), amount=_to_float(r[1]), category=str(r[2]), tx_timestamp=_format_ts(r[3]))
        for r in recent_rows
    ]

    return {
        "kpi": {"tx_count": month_tx_count, "total": month_spent},
        "categories": categories,
        "trend": trend,
        "trend_peak": trend_peak,
        "budgets": budgets,
        "budget_used_pct": budget_used_pct,
        "budget_limit_total": budget_limit_total,
        "budget_spent_total": budget_spent_total,
        "recent": recent,
        "top_category": top_category,
        "top_category_amount": top_category_amount,
        "month_label": month_start.strftime("%B %Y"),
        "unavailable": False,
    }
