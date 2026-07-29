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
        _refresh_button(),
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
