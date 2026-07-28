"""Fixed top bar shared across every authenticated page of the Reflex shell.

Mirrors the Streamlit header (brand left, actions right) but built with
real `rx.el.a` links so navigation is instant and browser-history-aware
instead of relying on session-state screen switching.
"""

import reflex as rx

from app.components.brand import brand
from app.states.nav_state import NavState
from app.theme import ROUTES


def _nav_link(label: str, href: str) -> rx.Component:
    return rx.el.a(
        label,
        href=href,
        class_name=(
            "text-sm font-medium text-[color:var(--purch-muted)] "
            "hover:text-[color:var(--purch-coral)] transition-colors px-2 py-1 rounded-md"
        ),
    )


def header() -> rx.Component:
    return rx.el.header(
        rx.el.div(
            # Left cluster: sidebar toggle + brand
            rx.el.div(
                rx.el.button(
                    rx.cond(NavState.sidebar_open, "✕", "☰"),
                    on_click=NavState.toggle_sidebar,
                    class_name=(
                        "text-lg text-[color:var(--purch-muted)] "
                        "hover:text-[color:var(--purch-coral)] px-2 py-1 rounded-md transition-colors"
                    ),
                ),
                rx.el.a(
                    brand(), href=ROUTES["index"], class_name="no-underline"
                ),
                class_name="flex items-center gap-3",
            ),
            # Right cluster: nav links
            rx.el.nav(
                _nav_link("Chat", ROUTES["chat"]),
                _nav_link("Analytics", ROUTES["analytics"]),
                _nav_link("Sign in", ROUTES["login"]),
                class_name="flex items-center gap-1",
            ),
            class_name=(
                "max-w-[1600px] mx-auto h-12 px-4 sm:px-6 "
                "flex items-center justify-between"
            ),
        ),
        class_name=(
            "fixed top-0 left-0 right-0 z-50 h-12 "
            "bg-[color:var(--purch-paper)] border-b border-[color:var(--purch-border)]"
        ),
    )
