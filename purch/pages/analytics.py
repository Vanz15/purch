"""Analytics page placeholder — charts land in a later phase against
the existing `db.models` query helpers (imported via `backend.db`)."""

import reflex as rx

from purch.components.layout import page_shell
from purch.theme import CLASSES


def _stat_card(label: str, value: str, hint: str) -> rx.Component:
    return rx.el.div(
        rx.el.div(label, class_name=CLASSES["eyebrow"]),
        rx.el.div(value, class_name="font-['DM_Mono'] text-2xl font-bold mt-1"),
        rx.el.div(
            hint, class_name="text-xs text-[color:var(--purch-muted)] mt-1"
        ),
        class_name=f"{CLASSES['card']} p-5",
    )


def analytics_page() -> rx.Component:
    return page_shell(
        rx.el.div(
            rx.el.div("Spending overview", class_name=CLASSES["eyebrow"]),
            rx.el.h1(
                "Analytics",
                class_name=f"{CLASSES['display_heading']} text-3xl mt-1",
            ),
            rx.el.p(
                "Trend, category breakdown, and month-over-month comparisons will land here next.",
                class_name="text-sm text-[color:var(--purch-secondary-text)] mt-2 max-w-xl",
            ),
            rx.el.div(
                _stat_card("This month", "₱0", "Live data lands with phase 3"),
                _stat_card("Top category", "—", "Awaiting transactions"),
                _stat_card("Budget used", "0%", "Set budgets from chat"),
                _stat_card("Vs last month", "—", "Comparison coming soon"),
                class_name="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-6",
            ),
            rx.el.div(
                rx.el.div("📊", class_name="text-4xl"),
                rx.el.div(
                    "Analytics coming soon",
                    class_name=f"{CLASSES['display_heading']} text-lg mt-2",
                ),
                rx.el.div(
                    "The Reflex shell is in place — charts get wired against the existing SQLite backend in the next phase.",
                    class_name="text-sm text-[color:var(--purch-muted)] mt-1 max-w-md text-center",
                ),
                class_name=f"{CLASSES['card']} mt-6 p-12 flex flex-col items-center justify-center text-center",
            ),
        ),
        with_sidebar=True,
    )
