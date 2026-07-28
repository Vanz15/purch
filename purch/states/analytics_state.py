"""Analytics state — read-only aggregate queries against the shared
Postgres/Supabase backend (with SQLite fallback for local development).

Every query is a single aggregate round-trip. Nothing here inserts,
updates, deletes, or issues DDL — the schema is managed out-of-band
by Supabase and this module is purely read-only per plan constraints.

Design decisions worth flagging:

* SQL is written in a portable subset that works on both Postgres and
  SQLite (the migration fallback). `date_trunc` and `INTERVAL` aren't
  portable, so we compute the month/day boundaries in Python and bind
  them as `:params` — the database still does all the aggregation.
* Trend data is densified in Python: SQL returns one row per day with
  activity, and we fill in the 30-day window's zero-days so the chart
  never renders a jagged/broken axis.
* All numeric conversions guard against NULL / Decimal via
  `_to_float` / `_to_int` — Postgres NUMERIC comes back as Decimal.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import TypedDict

import reflex as rx
from sqlalchemy import text
from sqlalchemy.engine import Engine

from purch import backend

ANON_USER = "anonymous@purch.local"
_TREND_DAYS = 30
_RECENT_LIMIT = 10


class KpiSnapshot(TypedDict):
    tx_count: int
    total: float


class CategoryRow(TypedDict):
    category: str
    total: float
    count: int
    pct_of_total: int


class TrendPoint(TypedDict):
    day: str  # "MMM DD" — display label for the axis
    iso: str  # ISO date for stable ordering
    total: float
    count: int


class BudgetStatusRow(TypedDict):
    category: str
    limit_amount: float
    spent: float
    pct: int
    remaining: float
    status: str  # "on_track" | "near" | "over"


class RecentTx(TypedDict):
    item: str
    amount: float
    category: str
    tx_timestamp: str  # "YYYY-MM-DD HH:MM" (PH-local)


def _to_float(v) -> float:
    if v is None:
        return 0.0
    if isinstance(v, Decimal):
        return float(v)
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
    """Match the shape of `db.models.to_local_time_str` — accept either
    a stored string (SQLite path) or a `datetime` (Postgres) and return
    a Philippines-local `YYYY-MM-DD HH:MM` string."""
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


def _engine_or_none() -> Engine | None:
    """Return the configured SQLAlchemy engine when Postgres is active,
    or `None` when we're on the SQLite fallback (analytics is
    Postgres-only for now — SQLite users see a friendly notice)."""
    try:
        if backend.is_postgres():
            from purch.db_backend import get_engine

            return get_engine()
    except Exception as e:
        logging.exception(f"engine lookup failed: {e}")
    return None


class AnalyticsState(rx.State):
    # Lifecycle
    is_loading: bool = False
    has_loaded: bool = False
    error_text: str = ""
    empty: bool = False
    unavailable: bool = False  # true when Postgres backend isn't wired up

    # Headline KPIs
    month_spent: float = 0.0
    month_tx_count: int = 0
    top_category: str = "—"
    top_category_amount: float = 0.0
    budget_used_pct: int = 0
    budget_limit_total: float = 0.0
    budget_spent_total: float = 0.0
    budget_remaining_total: float = 0.0

    # Detail sections
    category_rows: list[CategoryRow] = []
    trend_points: list[TrendPoint] = []
    trend_peak: float = 0.0
    budget_status: list[BudgetStatusRow] = []
    recent_transactions: list[RecentTx] = []

    month_label: str = ""
    last_refreshed: str = ""

    @rx.var
    def has_trend_data(self) -> bool:
        return any(p["total"] > 0 for p in self.trend_points)

    @rx.var
    def has_categories(self) -> bool:
        return len(self.category_rows) > 0

    @rx.var
    def has_budgets(self) -> bool:
        return len(self.budget_status) > 0

    @rx.var
    def has_recent(self) -> bool:
        return len(self.recent_transactions) > 0

    async def _resolve_user(self) -> str:
        try:
            from purch.states.auth_state import AuthState

            auth = await self.get_state(AuthState)
            return auth.user_email or ANON_USER
        except Exception as e:
            logging.exception(f"analytics user lookup failed: {e}")
            return ANON_USER

    # ------------------------------------------------------------------ #
    # Event handlers
    # ------------------------------------------------------------------ #

    @rx.event
    async def on_load(self):
        """Page-load entry point. Bootstraps DB, kicks off refresh,
        and forwards a sidebar refresh so budget widgets stay in
        sync with whatever analytics just displayed."""
        try:
            backend.bootstrap()
        except Exception as e:
            logging.exception(f"analytics bootstrap failed: {e}")
        yield AnalyticsState.refresh

    @rx.event
    async def refresh(self):
        """Manual + automatic refresh handler. Runs every aggregate
        query, then triggers the sidebar refresh so both surfaces
        agree on today's totals."""
        self.is_loading = True
        self.error_text = ""
        yield

        engine = _engine_or_none()
        if engine is None:
            self.unavailable = True
            self.is_loading = False
            self.has_loaded = True
            return

        self.unavailable = False
        user_id = await self._resolve_user()

        try:
            backend.ensure_user(user_id)
            today = date.today()
            month_start = today.replace(day=1)
            trend_start = today - timedelta(days=_TREND_DAYS - 1)

            with engine.connect() as conn:
                kpi_row = conn.execute(
                    text(
                        "SELECT COUNT(*) AS tx_count, "
                        "COALESCE(SUM(amount), 0) AS total "
                        "FROM transactions "
                        "WHERE user_id = :uid "
                        "AND tx_timestamp >= (:month_start)::timestamp"
                    ),
                    {"uid": user_id, "month_start": month_start.isoformat()},
                ).first()

                cat_rows = conn.execute(
                    text(
                        "SELECT category, COALESCE(SUM(amount), 0) AS total, "
                        "COUNT(*) AS cnt FROM transactions "
                        "WHERE user_id = :uid "
                        "AND tx_timestamp >= (:month_start)::timestamp "
                        "GROUP BY category ORDER BY total DESC"
                    ),
                    {"uid": user_id, "month_start": month_start.isoformat()},
                ).all()

                trend_rows = conn.execute(
                    text(
                        "SELECT CAST(tx_timestamp AS DATE) AS day, "
                        "COALESCE(SUM(amount), 0) AS total, "
                        "COUNT(*) AS cnt FROM transactions "
                        "WHERE user_id = :uid "
                        "AND tx_timestamp >= (:trend_start)::timestamp "
                        "GROUP BY CAST(tx_timestamp AS DATE) "
                        "ORDER BY day"
                    ),
                    {"uid": user_id, "trend_start": trend_start.isoformat()},
                ).all()

                budget_rows = conn.execute(
                    text(
                        "SELECT b.category, b.limit_amount, "
                        "COALESCE(SUM(t.amount), 0) AS spent "
                        "FROM budgets b "
                        "LEFT JOIN transactions t "
                        "ON t.user_id = b.user_id "
                        "AND t.category = b.category "
                        "AND t.tx_timestamp >= (:month_start)::timestamp "
                        "WHERE b.user_id = :uid AND b.period = 'monthly' "
                        "GROUP BY b.category, b.limit_amount "
                        "ORDER BY b.category"
                    ),
                    {"uid": user_id, "month_start": month_start.isoformat()},
                ).all()

                recent_rows = conn.execute(
                    text(
                        "SELECT item, amount, category, tx_timestamp "
                        "FROM transactions WHERE user_id = :uid "
                        "ORDER BY tx_timestamp DESC LIMIT :lim"
                    ),
                    {"uid": user_id, "lim": _RECENT_LIMIT},
                ).all()

            # ---- KPIs ------------------------------------------------
            self.month_tx_count = _to_int(kpi_row[0]) if kpi_row else 0
            self.month_spent = _to_float(kpi_row[1]) if kpi_row else 0.0

            # ---- Category breakdown ---------------------------------
            total_month = self.month_spent or 0.0
            categories: list[CategoryRow] = []
            for r in cat_rows:
                total = _to_float(r[1])
                pct = (
                    int(round((total / total_month) * 100))
                    if total_month
                    else 0
                )
                categories.append(
                    CategoryRow(
                        category=str(r[0]),
                        total=total,
                        count=_to_int(r[2]),
                        pct_of_total=pct,
                    )
                )
            self.category_rows = categories
            if categories:
                self.top_category = categories[0]["category"]
                self.top_category_amount = categories[0]["total"]
            else:
                self.top_category = "—"
                self.top_category_amount = 0.0

            # ---- Budget status --------------------------------------
            statuses: list[BudgetStatusRow] = []
            budget_limit_total = 0.0
            budget_spent_total = 0.0
            for r in budget_rows:
                limit_amt = _to_float(r[1])
                spent = _to_float(r[2])
                pct = int(round((spent / limit_amt) * 100)) if limit_amt else 0
                if pct >= 100:
                    status = "over"
                elif pct >= 80:
                    status = "near"
                else:
                    status = "on_track"
                statuses.append(
                    BudgetStatusRow(
                        category=str(r[0]),
                        limit_amount=limit_amt,
                        spent=spent,
                        pct=min(pct, 150),
                        remaining=limit_amt - spent,
                        status=status,
                    )
                )
                budget_limit_total += limit_amt
                budget_spent_total += spent
            self.budget_status = statuses
            self.budget_limit_total = budget_limit_total
            self.budget_spent_total = budget_spent_total
            self.budget_remaining_total = (
                budget_limit_total - budget_spent_total
            )
            self.budget_used_pct = (
                int(round((budget_spent_total / budget_limit_total) * 100))
                if budget_limit_total
                else 0
            )

            # ---- Trend (densified) ----------------------------------
            by_day: dict[str, tuple[float, int]] = {}
            for r in trend_rows:
                day_val = r[0]
                if isinstance(day_val, datetime):
                    iso = day_val.date().isoformat()
                elif isinstance(day_val, date):
                    iso = day_val.isoformat()
                else:
                    iso = str(day_val)
                by_day[iso] = (_to_float(r[1]), _to_int(r[2]))

            points: list[TrendPoint] = []
            peak = 0.0
            for i in range(_TREND_DAYS):
                d = trend_start + timedelta(days=i)
                iso = d.isoformat()
                total, count = by_day.get(iso, (0.0, 0))
                if total > peak:
                    peak = total
                points.append(
                    TrendPoint(
                        day=d.strftime("%b %d"),
                        iso=iso,
                        total=round(total, 2),
                        count=count,
                    )
                )
            self.trend_points = points
            self.trend_peak = peak

            # ---- Recent transactions --------------------------------
            recents: list[RecentTx] = []
            for r in recent_rows:
                recents.append(
                    RecentTx(
                        item=str(r[0]),
                        amount=_to_float(r[1]),
                        category=str(r[2]),
                        tx_timestamp=_format_ts(r[3]),
                    )
                )
            self.recent_transactions = recents

            # ---- Meta -----------------------------------------------
            self.month_label = today.strftime("%B %Y")
            self.last_refreshed = (
                datetime.now().strftime("%I:%M %p").lstrip("0")
            )
            self.empty = (
                self.month_tx_count == 0
                and not self.budget_status
                and not self.recent_transactions
            )
            self.has_loaded = True
        except Exception as e:
            logging.exception(f"analytics refresh failed: {e}")
            self.error_text = (
                "Couldn't load analytics right now. Please try again."
            )
        finally:
            self.is_loading = False

        # Keep the sidebar in sync with whatever we just showed.
        try:
            from purch.states.sidebar_state import SidebarState

            yield SidebarState.refresh
        except Exception as e:
            logging.exception(f"sidebar refresh chain failed: {e}")
