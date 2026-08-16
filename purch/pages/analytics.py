"""Analytics page — functional dashboard backed by the Postgres/Supabase
read-only aggregate queries in `purch.states.analytics_state`.

Composition-only: every section renders through
`purch.components.analytics_sections`, so the page file just handles
layout, the page header (title + refresh action), and the top-level
state-branching (loading / error / unavailable / empty / loaded).
"""

import reflex as rx

from purch.components.analytics_sections import (
    dashboard_body,
    empty_dashboard,
    error_banner,
    loading_skeleton,
    unauthenticated_banner,
    unavailable_banner,
)
from purch.components.layout import page_shell
from purch.states.analytics_state import AnalyticsState
from purch.states.auth_state import AuthState
from purch.theme import CLASSES


def _refresh_button() -> rx.Component:
    return rx.el.button(
        rx.cond(
            AnalyticsState.is_loading,
            rx.el.span("Refreshing…"),
            rx.el.span("↻ Refresh"),
        ),
        on_click=AnalyticsState.refresh,
        disabled=AnalyticsState.is_loading,
        type="button",
        class_name=(
            CLASSES["outline_button"]
            + " text-sm disabled:opacity-60 disabled:cursor-not-allowed"
        ),
    )


def _month_nav_button(label: str, delta: int, disabled) -> rx.Component:
    return rx.el.button(
        label,
        on_click=lambda: AnalyticsState.shift_month(delta),
        disabled=disabled,
        type="button",
        class_name=(
            "w-8 h-8 shrink-0 rounded-lg border "
            "border-[color:var(--purch-border)] bg-[color:var(--purch-paper)] "
            "text-[color:var(--purch-ink)] text-sm font-semibold "
            "hover:border-[color:var(--purch-coral)] "
            "hover:text-[color:var(--purch-coral)] transition-colors "
            "disabled:opacity-40 disabled:cursor-not-allowed "
            "disabled:hover:border-[color:var(--purch-border)] "
            "disabled:hover:text-[color:var(--purch-ink)]"
        ),
    )


def _month_selector() -> rx.Component:
    """Month browser: ← / → step through months, and a 'This month'
    reset appears only when viewing a past month."""
    return rx.el.div(
        rx.el.div(
            _month_nav_button(
                "\u2190",
                -1,
                AnalyticsState.is_loading | ~AnalyticsState.can_go_back,
            ),
            rx.el.div(
                rx.el.div("Viewing", class_name=CLASSES["eyebrow"]),
                rx.el.div(
                    AnalyticsState.selected_month_display,
                    class_name=(
                        "font-['Playfair_Display'] font-bold text-sm "
                        "text-[color:var(--purch-ink)] leading-tight"
                    ),
                ),
                class_name="px-2 text-center min-w-[8.5rem]",
            ),
            _month_nav_button(
                "\u2192",
                1,
                AnalyticsState.is_loading | AnalyticsState.is_current_month,
            ),
            class_name=(
                "flex items-center gap-1 rounded-xl border "
                "border-[color:var(--purch-border)] "
                "bg-[color:var(--purch-parchment)] p-1.5"
            ),
        ),
        rx.cond(
            AnalyticsState.is_current_month,
            rx.fragment(),
            rx.el.button(
                "This month",
                on_click=AnalyticsState.reset_to_current_month,
                disabled=AnalyticsState.is_loading,
                type="button",
                class_name=(
                    CLASSES["outline_button"]
                    + " text-xs py-2 disabled:opacity-60 "
                    + "disabled:cursor-not-allowed"
                ),
            ),
        ),
        class_name="flex flex-wrap items-center gap-2",
    )


def _page_header() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div("Spending overview", class_name=CLASSES["eyebrow"]),
            rx.el.h1(
                "Analytics",
                class_name=(
                    "font-['Playfair_Display'] font-bold tracking-tight "
                    "text-3xl sm:text-4xl text-[color:var(--purch-ink)] mt-1"
                ),
            ),
            rx.el.p(
                rx.cond(
                    AnalyticsState.refresh_status != "",
                    rx.el.span(
                        AnalyticsState.refresh_status,
                        class_name="text-[color:var(--purch-muted)] italic",
                    ),
                    rx.cond(
                        AnalyticsState.month_label != "",
                        rx.el.span(
                            AnalyticsState.month_label,
                            rx.cond(
                                AnalyticsState.last_refreshed != "",
                                rx.el.span(
                                    " · Updated ",
                                    AnalyticsState.last_refreshed,
                                    class_name="text-[color:var(--purch-muted)]",
                                ),
                                rx.fragment(),
                            ),
                        ),
                        rx.el.span(
                            "Live data from Supabase",
                            class_name="text-[color:var(--purch-muted)]",
                        ),
                    ),
                ),
                class_name="text-sm text-[color:var(--purch-secondary-text)] mt-2",
            ),
            class_name="flex-1 min-w-0",
        ),
        rx.el.div(
            _month_selector(),
            _refresh_button(),
            class_name="flex flex-wrap items-center gap-2",
        ),
        class_name=(
            "flex flex-col sm:flex-row sm:items-end sm:justify-between "
            "gap-3 mb-6"
        ),
    )


def _content() -> rx.Component:
    """Top-level branching. Order matters:
    unauthenticated → unavailable (SQLite fallback) → error →
    initial loading → empty (no data) → dashboard.
    """
    return rx.cond(
        ~AuthState.is_authenticated,
        unauthenticated_banner(),
        rx.cond(
            AnalyticsState.unavailable,
            unavailable_banner(),
            rx.cond(
                AnalyticsState.error_text != "",
                error_banner(),
                rx.cond(
                    (~AnalyticsState.has_loaded) & AnalyticsState.is_loading,
                    loading_skeleton(),
                    rx.cond(
                        AnalyticsState.empty,
                        empty_dashboard(),
                        dashboard_body(),
                    ),
                ),
            ),
        ),
    )


def analytics_page() -> rx.Component:
    return page_shell(
        rx.el.div(
            _page_header(),
            _content(),
            class_name="w-full max-w-6xl mx-auto",
            on_mount=[
                AnalyticsState.on_load,
                rx.call_script(
                    "Intl.DateTimeFormat().resolvedOptions().timeZone",
                    callback=AnalyticsState.set_timezone,
                ),
            ],
        ),
        with_sidebar=True,
    )
