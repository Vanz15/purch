"""Sidebar state — budgets, per-category spending, tone selection.

Reads directly from the shared SQLite backend via `purch.backend`.
Refreshes whenever the sidebar is opened or after a chat turn writes a
new transaction / budget.
"""

import logging
from typing import TypedDict

import reflex as rx

from purch import backend


class BudgetRow(TypedDict):
    category: str
    limit: float
    spent: float
    pct: int
    over: bool


ANON_USER = "anonymous@purch.local"


class SidebarState(rx.State):
    budget_rows: list[BudgetRow] = []
    total_spent: float = 0.0
    total_limit: float = 0.0
    total_pct: int = 0
    current_tone: str = "nonchalant"
    tone_options: list[str] = list(backend.VALID_TONES) + ["neutral"]
    categories: list[str] = list(backend.CATEGORIES)
    display_name: str = "Guest"
    is_loaded: bool = False

    @rx.var
    def has_any_budget(self) -> bool:
        return self.total_limit > 0

    async def _current_user(self) -> str:
        try:
            from purch.states.auth_state import AuthState

            auth = await self.get_state(AuthState)
            return auth.user_email or ANON_USER
        except Exception as e:
            logging.exception(f"Sidebar user lookup failed: {e}")
            return ANON_USER

    @rx.event
    async def refresh(self):
        user_id = await self._current_user()
        try:
            backend.ensure_user(user_id)
            data = backend.get_all_budgets_and_spending(
                user_id, self.categories
            )
            rows: list[BudgetRow] = []
            total_spent = 0.0
            total_limit = 0.0
            for cat in self.categories:
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
            self.budget_rows = rows
            self.total_spent = total_spent
            self.total_limit = total_limit
            self.total_pct = (
                int(min(round((total_spent / total_limit) * 100), 100))
                if total_limit
                else 0
            )
            self.current_tone = backend.get_user_tone(user_id)
            try:
                from purch.states.auth_state import AuthState

                auth = await self.get_state(AuthState)
                self.display_name = auth.user_name or (
                    auth.user_email.split("@")[0]
                    if auth.user_email
                    else "Guest"
                )
            except Exception:
                logging.exception("Unexpected error")
                self.display_name = "Guest"
            self.is_loaded = True
        except Exception as e:
            logging.exception(f"Sidebar refresh failed: {e}")

    @rx.event
    async def set_tone(self, tone: str):
        if tone not in self.tone_options:
            return
        user_id = await self._current_user()
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
