"""Sign-in page for the Purch shell."""

import reflex as rx

from purch.components.brand import brand
from purch.components.layout import page_shell
from purch.states.auth_state import AuthState
from purch.theme import CLASSES, ROUTES


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
                    on_click=AuthState.begin_google_login,
                    type="button",
                    class_name=f"{CLASSES['primary_button']} mt-6 w-full",
                ),
                rx.cond(
                    AuthState.oauth_status == "unavailable",
                    rx.el.p(
                        AuthState.oauth_error,
                        class_name="text-sm text-[color:var(--purch-secondary-text)] mt-4 leading-relaxed",
                    ),
                    rx.fragment(),
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
