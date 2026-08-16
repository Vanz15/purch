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
from purch.time_utils import (
    format_stored_timestamp,
    month_label,
    now_display,
    today_in_timezone,
)

_RECENT_LIMIT = 10
_MIN_YEAR = 2000


def _add_months(start: date, delta: int) -> date:
    """Return the first day of the month `delta` months from `start`."""
    total = (start.year * 12) + (start.month - 1) + delta
    return date(total // 12, (total % 12) + 1, 1)


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
    unauthenticated: bool = False  # true when no identity is active

    # Selected month (0/0 means "follow the current calendar month").
    # Every query below is scoped to this month, so browsing back in time
    # re-reads KPIs, categories, budgets, trend, and recent activity.
    selected_year: int = 0
    selected_month: int = 0
    is_past_month: bool = False

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
    refresh_status: str = ""
    refresh_generation: int = 0
    timezone_name: str = ""

    # Internal guard: prevents overlapping refreshes from stacking DB
    # duplicate on_load fires from re-mounts) from stacking DB round
    # trips and racing each other's state writes.
    _refresh_in_flight: bool = False

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

    def _resolved_month(self) -> date:
        """First day of the month currently being viewed."""
        if self.selected_year and self.selected_month:
            try:
                return date(self.selected_year, self.selected_month, 1)
            except ValueError:
                logging.exception("Invalid selected month; using current")
        return today_in_timezone(self.timezone_name).replace(day=1)

    @rx.var
    def is_current_month(self) -> bool:
        today = today_in_timezone(self.timezone_name)
        start = self._resolved_month()
        return start.year == today.year and start.month == today.month

    @rx.var
    def selected_month_display(self) -> str:
        """Always-available label for the header control (even before the
        first query resolves)."""
        return month_label(self._resolved_month(), self.timezone_name)

    @rx.var
    def can_go_back(self) -> bool:
        return self._resolved_month().year > _MIN_YEAR

    async def _resolve_user(self) -> str:
        """Return the signed-in user id or an empty string. No anonymous
        fallback — analytics renders a sign-in prompt when this is empty
        rather than aggregating a shared account."""
        try:
            from purch.states.auth_state import AuthState

            auth = await self.get_state(AuthState)
            return auth.user_email or ""
        except Exception as e:
            logging.exception(f"analytics user lookup failed: {e}")
            return ""

    # ------------------------------------------------------------------ #
    # Event handlers
    # ------------------------------------------------------------------ #

    @rx.event
    def set_timezone(self, timezone_name: str):
        self.timezone_name = timezone_name.strip()

    @rx.event
    def shift_month(self, delta: int):
        """Step the selected month backwards/forwards. Never moves past the
        current calendar month (there's nothing to show in the future)."""
        today = today_in_timezone(self.timezone_name)
        current = today.replace(day=1)
        target = _add_months(self._resolved_month(), int(delta))
        if target > current:
            target = current
        if target.year < _MIN_YEAR:
            return
        if (target.year, target.month) == (
            self.selected_year,
            self.selected_month,
        ):
            return
        self.selected_year = target.year
        self.selected_month = target.month
        yield AnalyticsState.refresh

    @rx.event
    def reset_to_current_month(self):
        today = today_in_timezone(self.timezone_name)
        if (today.year, today.month) == (
            self.selected_year,
            self.selected_month,
        ):
            return
        self.selected_year = today.year
        self.selected_month = today.month
        yield AnalyticsState.refresh

    @rx.event
    async def on_load(self):
        """Page-load entry point. Bootstraps DB and kicks off a single
        refresh. Deliberately does NOT chain a sidebar refresh — the
        sidebar component owns its own `on_mount` refresh, and chaining
        one here would double every page load.

        Also guards against re-entry: if a refresh is already flying
        (e.g. rx re-mounted the container), we skip so both fires don't
        race each other's state writes."""
        if self.is_loading or self._refresh_in_flight:
            return
        try:
            backend.bootstrap()
        except Exception as e:
            logging.exception(f"analytics bootstrap failed: {e}")
        yield AnalyticsState.refresh

    @rx.event
    async def refresh(self):
        """Manual + automatic refresh handler.

        Design notes for websocket stability:
          * Cached values (KPIs, categories, trend, budgets, recent) are
            NOT cleared before the query — the UI keeps showing the last
            good dashboard while the refresh spinner runs, so a slow or
            failing round-trip never blanks the page.
          * Re-entry is guarded: if a refresh is already in flight we
            drop this one silently.
          * The whole DB block is wrapped so any timeout / connection
            error resolves to a friendly banner AND `is_loading` is
            always released in `finally` — the loading state can never
            stick even if Postgres hangs mid-query.
        """
        if self._refresh_in_flight:
            return
        self._refresh_in_flight = True
        self.refresh_generation += 1
        request_generation = self.refresh_generation
        self.is_loading = True
        self.refresh_status = "Refreshing…"
        self.error_text = ""
        yield

        engine = _engine_or_none()
        if engine is None:
            self.unavailable = True
            self.is_loading = False
            self.has_loaded = True
            self._refresh_in_flight = False
            return

        self.unavailable = False
        user_id = await self._resolve_user()

        if not user_id:
            self.unauthenticated = True
            self.is_loading = False
            self.has_loaded = True
            self.empty = False
            self.category_rows = []
            self.trend_points = []
            self.budget_status = []
            self.recent_transactions = []
            self.month_spent = 0.0
            self.month_tx_count = 0
            self.top_category = "—"
            self.top_category_amount = 0.0
            self.budget_used_pct = 0
            self.budget_limit_total = 0.0
            self.budget_spent_total = 0.0
            self.budget_remaining_total = 0.0
            self.trend_peak = 0.0
            self._refresh_in_flight = False
            return

        self.unauthenticated = False
        try:
            today = today_in_timezone(self.timezone_name)
            current_month = today.replace(day=1)
            month_start = self._resolved_month()
            if month_start > current_month:
                month_start = current_month
            month_end = _add_months(month_start, 1)
            # Keep the selection explicit so the header control and the
            # data can never drift apart after the first load.
            self.selected_year = month_start.year
            self.selected_month = month_start.month
            # For the current month the trend stops at today; for a past
            # month it covers the whole month.
            trend_end = (
                today
                if month_start == current_month
                else month_end - timedelta(days=1)
            )
            window = {
                "uid": user_id,
                "month_start": month_start.isoformat(),
                "month_end": month_end.isoformat(),
            }

            with engine.connect() as conn:
                kpi_row = conn.execute(
                    text(
                        "SELECT COUNT(*) AS tx_count, "
                        "COALESCE(SUM(amount), 0) AS total "
                        "FROM transactions "
                        "WHERE user_id = :uid "
                        "AND tx_timestamp >= (:month_start)::timestamp "
                        "AND tx_timestamp < (:month_end)::timestamp"
                    ),
                    window,
                ).first()

                cat_rows = conn.execute(
                    text(
                        "SELECT category, COALESCE(SUM(amount), 0) AS total, "
                        "COUNT(*) AS cnt FROM transactions "
                        "WHERE user_id = :uid "
                        "AND tx_timestamp >= (:month_start)::timestamp "
                        "AND tx_timestamp < (:month_end)::timestamp "
                        "GROUP BY category ORDER BY total DESC"
                    ),
                    window,
                ).all()

                trend_rows = conn.execute(
                    text(
                        "SELECT CAST(tx_timestamp AS DATE) AS day, "
                        "COALESCE(SUM(amount), 0) AS total, "
                        "COUNT(*) AS cnt FROM transactions "
                        "WHERE user_id = :uid "
                        "AND tx_timestamp >= (:month_start)::timestamp "
                        "AND tx_timestamp < (:month_end)::timestamp "
                        "GROUP BY CAST(tx_timestamp AS DATE) "
                        "ORDER BY day"
                    ),
                    window,
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
                        "AND t.tx_timestamp < (:month_end)::timestamp "
                        "WHERE b.user_id = :uid AND b.period = 'monthly' "
                        "GROUP BY b.category, b.limit_amount "
                        "ORDER BY b.category"
                    ),
                    window,
                ).all()

                recent_rows = conn.execute(
                    text(
                        "SELECT item, amount, category, tx_timestamp "
                        "FROM transactions WHERE user_id = :uid "
                        "AND tx_timestamp >= (:month_start)::timestamp "
                        "AND tx_timestamp < (:month_end)::timestamp "
                        "ORDER BY tx_timestamp DESC LIMIT :lim"
                    ),
                    {**window, "lim": _RECENT_LIMIT},
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
            span = max((trend_end - month_start).days + 1, 1)
            for i in range(span):
                d = month_start + timedelta(days=i)
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
                        tx_timestamp=format_stored_timestamp(
                            r[3], self.timezone_name
                        ),
                    )
                )
            self.recent_transactions = recents

            # ---- Meta -----------------------------------------------
            self.month_label = month_label(month_start, self.timezone_name)
            self.is_past_month = month_start < current_month
            self.last_refreshed = now_display(self.timezone_name)
            self.empty = (
                self.month_tx_count == 0
                and not self.budget_status
                and not self.recent_transactions
            )
            self.has_loaded = True
        except Exception as e:
            logging.exception(f"analytics refresh failed: {e}")
            # Timeout / connection errors get a slightly more specific
            # message so users know it wasn't their input. Cached data
            # stays on screen — we only surface a banner.
            msg = str(e).lower()
            if "timeout" in msg or "timed out" in msg:
                self.error_text = (
                    "Analytics took too long to load. Showing the last "
                    "snapshot — try Refresh in a moment."
                )
            elif "connection" in msg or "operationalerror" in msg:
                self.error_text = (
                    "Couldn't reach the database just now. Showing the "
                    "last snapshot — try Refresh in a moment."
                )
            else:
                self.error_text = (
                    "Couldn't load analytics right now. Please try again."
                )
        finally:
            # Always release the loading state so a failed client refresh
            # cannot leave its own websocket waiting indefinitely.
            self.is_loading = False
            self._refresh_in_flight = False
            if self.error_text:
                self.refresh_status = "Showing the last saved snapshot"
            else:
                self.refresh_status = ""
