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

from purch import backend, wallet_backend
from purch.time_utils import (
    format_stored_timestamp,
    month_label,
    now_display,
    today_in_timezone,
)

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


class WalletBar(TypedDict):
    id: int
    name: str
    wallet_type: str
    balance: float
    balance_display: str
    pct: int
    accent: str
    note: str
    is_liability: bool
    movement_count: int
    movement_display: str
    group: str


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

    # Wallet / bank status
    wallet_bars: list[WalletBar] = []
    wallets_unavailable: bool = False
    wallet_assets: float = 0.0
    wallet_liabilities: float = 0.0
    wallet_net: float = 0.0
    wallet_assets_display: str = "0.00"
    wallet_liabilities_display: str = "0.00"
    wallet_net_display: str = "0.00"
    wallet_peak: float = 0.0

    # Grouped wallet views: Debit (Bank/Cash/Savings), Lent, Borrowed
    # (Debt/Loan). Split into separate lists so the UI can render each
    # group with its own heading + insight without nested foreach.
    debit_bars: list[WalletBar] = []
    lent_bars: list[WalletBar] = []
    borrowed_bars: list[WalletBar] = []
    debit_total_display: str = "0.00"
    lent_total_display: str = "0.00"
    borrowed_total_display: str = "0.00"
    debit_insight: str = ""
    lent_insight: str = ""
    borrowed_insight: str = ""

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

    @rx.var
    def has_wallets(self) -> bool:
        return len(self.wallet_bars) > 0

    @rx.var
    def has_wallet_liabilities(self) -> bool:
        return self.wallet_liabilities > 0

    @rx.var
    def has_debit_wallets(self) -> bool:
        return len(self.debit_bars) > 0

    @rx.var
    def has_lent_wallets(self) -> bool:
        return len(self.lent_bars) > 0

    @rx.var
    def has_borrowed_wallets(self) -> bool:
        return len(self.borrowed_bars) > 0

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
            self.wallet_bars = []
            self.wallet_assets = 0.0
            self.wallet_liabilities = 0.0
            self.wallet_net = 0.0
            self.wallet_assets_display = "0.00"
            self.wallet_liabilities_display = "0.00"
            self.wallet_net_display = "0.00"
            self._build_wallet_groups([])
            self._refresh_in_flight = False
            return

        self.unauthenticated = False
        try:
            today = today_in_timezone(self.timezone_name)
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
                        tx_timestamp=format_stored_timestamp(
                            r[3], self.timezone_name
                        ),
                    )
                )
            self.recent_transactions = recents

            # ---- Wallet / bank status -------------------------------
            self._load_wallets(user_id)

            # ---- Meta -----------------------------------------------
            self.month_label = month_label(today, self.timezone_name)
            self.last_refreshed = now_display(self.timezone_name)
            self.empty = (
                self.month_tx_count == 0
                and not self.budget_status
                and not self.recent_transactions
                and not self.wallet_bars
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

    def _load_wallets(self, user_id: str) -> None:
        """Load wallet balances (and this month's ledger movement counts)
        for the wallet status section.

        Isolated in its own try/except so a missing/unavailable wallet
        table can never take down the rest of the spending dashboard.
        """
        try:
            if not wallet_backend.available():
                self.wallets_unavailable = True
                self.wallet_bars = []
                self._build_wallet_groups([])
                return
            wallets = wallet_backend.list_wallets(user_id)
        except Exception as e:
            logging.exception(f"analytics wallet read failed: {e}")
            self.wallets_unavailable = True
            self.wallet_bars = []
            self._build_wallet_groups([])
            return

        self.wallets_unavailable = False
        movements: dict[int, tuple[int, float]] = {}
        try:
            engine = _engine_or_none()
            if engine is not None and wallets:
                month_start = today_in_timezone(self.timezone_name).replace(
                    day=1
                )
                with engine.connect() as conn:
                    rows = conn.execute(
                        text(
                            "SELECT wallet_id, COUNT(*) AS cnt, "
                            "COALESCE(SUM(amount_delta), 0) AS delta "
                            "FROM wallet_ledger "
                            "WHERE user_id = :uid "
                            "AND created_at >= (:som)::timestamp "
                            "GROUP BY wallet_id"
                        ),
                        {"uid": user_id, "som": month_start.isoformat()},
                    ).all()
                for r in rows:
                    movements[int(r[0])] = (_to_int(r[1]), _to_float(r[2]))
        except Exception as e:
            logging.exception(f"wallet ledger movement read failed: {e}")
            movements = {}

        totals = wallet_backend.summary(wallets)
        peak = max((abs(float(w["balance"])) for w in wallets), default=0.0)
        bars: list[WalletBar] = []
        for w in wallets:
            balance = float(w["balance"])
            count, delta = movements.get(int(w["id"]), (0, 0.0))
            pct = (
                int(min(round((abs(balance) / peak) * 100), 100)) if peak else 0
            )
            sign = "-" if delta < 0 else "+"
            bars.append(
                WalletBar(
                    id=int(w["id"]),
                    name=str(w["name"]),
                    wallet_type=str(w["wallet_type"]),
                    balance=round(balance, 2),
                    balance_display=wallet_backend.money(balance),
                    pct=pct,
                    accent=wallet_backend.TYPE_ACCENT.get(
                        w["wallet_type"], "muted"
                    ),
                    note=str(w.get("note") or ""),
                    is_liability=str(w["wallet_type"]) in ("Debt", "Loan"),
                    movement_count=count,
                    movement_display=(
                        f"{sign}\u20b1{wallet_backend.money(abs(delta))}"
                        if count
                        else "No movement this month"
                    ),
                    group=wallet_backend.group_for(w["wallet_type"]),
                )
            )
        self.wallet_bars = bars
        self._build_wallet_groups(bars)
        self.wallet_peak = peak
        self.wallet_assets = totals["assets"]
        self.wallet_liabilities = totals["liabilities"]
        self.wallet_net = totals["net"]
        self.wallet_assets_display = wallet_backend.money(totals["assets"])
        self.wallet_liabilities_display = wallet_backend.money(
            totals["liabilities"]
        )
        self.wallet_net_display = wallet_backend.money(totals["net"])

    def _build_wallet_groups(self, bars: list[WalletBar]) -> None:
        """Split wallets into Debit / Lent / Borrowed and write a short,
        human balance insight for each group."""
        debit = [b for b in bars if b["group"] == "Debit"]
        lent = [b for b in bars if b["group"] == "Lent"]
        borrowed = [b for b in bars if b["group"] == "Borrowed"]

        self.debit_bars = debit
        self.lent_bars = lent
        self.borrowed_bars = borrowed

        debit_total = sum(b["balance"] for b in debit)
        lent_total = sum(b["balance"] for b in lent)
        borrowed_total = sum(b["balance"] for b in borrowed)

        self.debit_total_display = wallet_backend.money(debit_total)
        self.lent_total_display = wallet_backend.money(lent_total)
        self.borrowed_total_display = wallet_backend.money(borrowed_total)

        if not debit:
            self.debit_insight = (
                "No cash, bank, or savings wallets yet — add one to track "
                "what you can spend."
            )
        else:
            top = max(debit, key=lambda b: b["balance"])
            share = (
                int(round((top["balance"] / debit_total) * 100))
                if debit_total
                else 0
            )
            self.debit_insight = (
                f"{len(debit)} wallet(s) holding ₱"
                f"{wallet_backend.money(debit_total)} — "
                f"{top['name']} carries {share}% of it."
            )

        if not lent:
            self.lent_insight = "Nothing lent out right now."
        else:
            self.lent_insight = (
                f"₱{wallet_backend.money(lent_total)} is out with "
                f"{len(lent)} wallet(s) — money you still expect back."
            )

        if not borrowed:
            self.borrowed_insight = "No debts or loans tracked — you're clear."
        else:
            cover = (
                int(round((debit_total / borrowed_total) * 100))
                if borrowed_total
                else 0
            )
            self.borrowed_insight = (
                f"₱{wallet_backend.money(borrowed_total)} owed across "
                f"{len(borrowed)} wallet(s) — your debit wallets cover "
                f"{cover}% of it."
            )
