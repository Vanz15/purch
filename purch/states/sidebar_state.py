"""Sidebar state — budgets, per-category spending, tone selection.

Reads directly from the shared SQLite backend via `purch.backend`.
Refreshes whenever the sidebar is opened or after a chat turn writes a
new transaction / budget.
"""

import asyncio
import logging
from typing import TypedDict

import reflex as rx

from purch import backend, wallet_backend
from purch.time_utils import month_label, today_in_timezone


class BudgetRow(TypedDict):
    category: str
    limit: float
    spent: float
    pct: int
    over: bool


class WalletMiniRow(TypedDict):
    id: int
    name: str
    wallet_type: str
    balance_display: str
    pct: int
    accent: str
    is_liability: bool


class SidebarState(rx.State):
    budget_rows: list[BudgetRow] = []
    total_spent: float = 0.0
    total_limit: float = 0.0
    total_pct: int = 0
    current_tone: str = "nonchalant"
    # Only these tones are available for selection right now; other
    # personalities are temporarily disabled while their prompts are
    # refined. The picker hides everything else and set_tone rejects
    # anything not on this list.
    tone_options: list[str] = ["neutral", "bestie", "sarcastic"]
    categories: list[str] = list(backend.CATEGORIES)
    display_name: str = "Guest"
    is_loaded: bool = False
    refresh_status: str = ""
    refresh_generation: int = 0
    timezone_name: str = ""
    month_display: str = ""

    # Wallet snapshot (spendable / owed / net + per-wallet mini bars).
    wallet_rows: list[WalletMiniRow] = []
    wallets_available: bool = True
    spendable_display: str = "0.00"
    liabilities_display: str = "0.00"
    wallet_net_display: str = "0.00"
    has_liabilities: bool = False

    # Internal guard: keeps overlapping refreshes (mount + toggle +
    # chat-turn chain firing at once) from stacking DB round trips.
    _refresh_in_flight: bool = False

    @rx.var
    def has_any_budget(self) -> bool:
        return self.total_limit > 0

    @rx.var
    def has_wallets(self) -> bool:
        return len(self.wallet_rows) > 0

    async def _current_user_for_event(self) -> str:
        """Return the active identity for a regular event handler."""
        try:
            from purch.states.auth_state import AuthState

            auth = await self.get_state(AuthState)
            return auth.user_email or ""
        except Exception as e:
            logging.exception(f"Sidebar user lookup failed: {e}")
            return ""

    def _reset_data(self) -> None:
        self.budget_rows = []
        self.total_spent = 0.0
        self.total_limit = 0.0
        self.total_pct = 0
        self.current_tone = "nonchalant"
        self.display_name = "Guest"
        self.wallet_rows = []
        self.spendable_display = "0.00"
        self.liabilities_display = "0.00"
        self.wallet_net_display = "0.00"
        self.has_liabilities = False

    @rx.event
    def set_timezone(self, timezone_name: str):
        self.timezone_name = timezone_name.strip()

    @rx.event(background=True)
    async def refresh(self):
        # Read the latest auth snapshot while holding this state's lock. The
        # lock is released before any database work begins.
        async with self:
            if self._refresh_in_flight:
                return
            self._refresh_in_flight = True
            self.refresh_generation += 1
            request_generation = self.refresh_generation
            self.refresh_status = "Refreshing…"
            categories = list(self.categories)
            timezone_name = self.timezone_name
            from purch.states.auth_state import AuthState

            auth = await self.get_state(AuthState)
            user_id = auth.user_email or ""
            display_name = auth.display_name

        if not user_id:
            async with self:
                self._reset_data()
                self.is_loaded = True
                self.refresh_status = ""
                self._refresh_in_flight = False
            return
        try:
            data, tone = await asyncio.to_thread(
                self._read_snapshot, user_id, categories
            )
            wallet_rows, wallet_totals, wallets_ok = await asyncio.to_thread(
                self._read_wallets, user_id
            )
            rows: list[BudgetRow] = []
            total_spent = 0.0
            total_limit = 0.0
            for cat in categories:
                d = data.get(cat, {"limit": None, "spent": 0.0})
                limit = float(d["limit"]) if d["limit"] else 0.0
                spent = float(d["spent"] or 0.0)
                pct = (
                    int(min(round((spent / limit) * 100), 150)) if limit else 0
                )
                rows.append(
                    BudgetRow(
                        category=cat,
                        limit=limit,
                        spent=spent,
                        pct=pct,
                        over=(limit > 0 and spent > limit),
                    )
                )
                total_spent += spent
                total_limit += limit

            async with self:
                if request_generation != self.refresh_generation:
                    return
                self.budget_rows = rows
                self.total_spent = total_spent
                self.total_limit = total_limit
                self.total_pct = (
                    int(min(round((total_spent / total_limit) * 100), 100))
                    if total_limit
                    else 0
                )
                self.current_tone = tone
                self.display_name = display_name
                self.wallets_available = wallets_ok
                self.wallet_rows = wallet_rows
                self.spendable_display = wallet_backend.money(
                    wallet_totals["assets"]
                )
                self.liabilities_display = wallet_backend.money(
                    wallet_totals["liabilities"]
                )
                self.wallet_net_display = wallet_backend.money(
                    wallet_totals["net"]
                )
                self.has_liabilities = wallet_totals["liabilities"] > 0
                self.month_display = month_label(
                    today_in_timezone(timezone_name), timezone_name
                )
                self.is_loaded = True
                self.refresh_status = ""
        except Exception as e:
            logging.exception(f"Sidebar refresh failed: {e}")
            async with self:
                self.refresh_status = "Showing the last saved snapshot"
        finally:
            async with self:
                self._refresh_in_flight = False

    def _read_snapshot(
        self, user_id: str, categories: list[str]
    ) -> tuple[dict[str, dict[str, float | None]], str]:
        try:
            data = backend.get_all_budgets_and_spending(user_id, categories)
            tone = backend.get_user_tone(user_id)
            return data, tone
        except Exception as e:
            logging.exception(f"Sidebar snapshot read failed: {e}")
            raise

    def _read_wallets(
        self, user_id: str
    ) -> tuple[list[WalletMiniRow], dict[str, float], bool]:
        """Read the user's active wallets for the sidebar summary.

        Returns ([] , zeroed totals, False) when the wallet tables aren't
        reachable so the sidebar can render a friendly notice instead of
        failing the whole refresh."""
        empty = {"assets": 0.0, "liabilities": 0.0, "net": 0.0}
        try:
            if not wallet_backend.available():
                return [], empty, False
            wallets = wallet_backend.list_wallets(user_id)
        except Exception as e:
            logging.exception(f"Sidebar wallet read failed: {e}")
            return [], empty, False

        totals = wallet_backend.summary(wallets)
        peak = max((abs(float(w["balance"])) for w in wallets), default=0.0)
        rows: list[WalletMiniRow] = []
        for w in wallets:
            balance = float(w["balance"])
            pct = (
                int(min(round((abs(balance) / peak) * 100), 100)) if peak else 0
            )
            rows.append(
                WalletMiniRow(
                    id=int(w["id"]),
                    name=str(w["name"]),
                    wallet_type=str(w["wallet_type"]),
                    balance_display=wallet_backend.money(balance),
                    pct=pct,
                    accent=wallet_backend.TYPE_ACCENT.get(
                        w["wallet_type"], "muted"
                    ),
                    is_liability=str(w["wallet_type"]) in ("Debt", "Loan"),
                )
            )
        return rows, totals, True

    @rx.event
    async def set_tone(self, tone: str):
        if tone not in self.tone_options:
            return
        user_id = await self._current_user_for_event()
        if not user_id:
            return rx.toast.error(
                "Sign in first to save a tone preference.", duration=3000
            )
        try:
            backend.ensure_user(user_id)
            backend.set_user_tone(user_id, tone)
            self.current_tone = tone
            return rx.toast.success(
                f"Tone set to {tone.title()}", duration=2000
            )
        except Exception as e:
            logging.exception(f"Set tone failed: {e}")
            return rx.toast.error(
                "Couldn't save that tone right now. Please try again.",
                duration=3000,
            )
