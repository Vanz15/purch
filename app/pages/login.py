"""Placeholder login page. Real Google OAuth wiring lands in a later
phase (see MIGRATION.md — the Streamlit `st.login()` flow can't be
reused directly under Reflex)."""

import reflex as rx

from app.components.brand import brand
from app.components.layout import page_shell
from app.theme import CLASSES, ROUTES


def login_page() -> rx.Component:
    return page_shell(
        rx.el.div(
            rx.el.div(
                brand(show_beta=False, size="lg"),
                rx.el.h1(
                    "Welcome back.",
                    class_name=f"{CLASSES['display_heading']} text-3xl mt-6",
                ),
                rx.el.p(
                    "Sign in to pick up your chat, budgets, and tone right where you left off.",
                    class_name="text-sm text-[color:var(--purch-secondary-text)] mt-2 max-w-sm",
                ),
                rx.el.button(
                    "Continue with Google",
                    disabled=True,
                    class_name=f"{CLASSES['primary_button']} mt-6 w-full opacity-70 cursor-not-allowed",
                ),
                rx.el.p(
                    "Google OAuth is wired in a later migration phase.",
                    class_name=f"{CLASSES['eyebrow']} mt-4",
                ),
                rx.el.a(
                    "Back to home",
                    href=ROUTES["index"],
                    class_name="text-sm text-[color:var(--purch-muted)] hover:text-[color:var(--purch-coral)] mt-6 inline-block",
                ),
                class_name=f"{CLASSES['card']} p-8 w-full max-w-md",
            ),
            class_name="min-h-[calc(100vh-3rem)] flex items-center justify-center px-4",
        ),
        wide=True,
    )
