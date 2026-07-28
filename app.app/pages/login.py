"""Login page — polished two-panel branded experience.

Left panel: dark espresso hero with the Purch identity, headline, and
tone chips (mirrors the Streamlit login screen's left column).
Right panel: parchment surface with the chat preview and the sign-in
card. Google sign-in is wired to `AuthState.begin_google_login`, which
currently surfaces a friendly "not yet available" message — see
`app/MIGRATION.md` §7 for the three OAuth options being weighed.
"""

import reflex as rx

from app.app.components.brand import brand
from app.app.components.layout import page_shell
from app.app.states.auth_state import AuthState
from app.app.theme import CLASSES, ROUTES

_TONE_CHIPS: list[str] = [
    "Nonchalant",
    "Bestie",
    "Sarcastic",
    "Coach",
    "Rich Tita",
    "Kapampangan",
]


def _tone_chip(label: str) -> rx.Component:
    return rx.el.span(label, class_name="purch-chip")


def _hero_panel() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.div(
                "Purch",
                class_name=(
                    "font-['Playfair_Display'] font-bold text-3xl "
                    "text-[color:var(--purch-gold)]"
                ),
            ),
            rx.el.div(
                rx.el.div(
                    "Budget tracking, reimagined",
                    class_name=(
                        "font-['DM_Mono'] text-[0.7rem] uppercase tracking-[0.12em] "
                        "text-[color:var(--purch-gold)] mb-3"
                    ),
                ),
                rx.el.h1(
                    "Your last ",
                    rx.el.em(
                        "eventually",
                        class_name="italic text-[color:var(--purch-coral-light)]",
                    ),
                    rx.el.br(),
                    "leads to another.",
                    class_name=(
                        "font-['Playfair_Display'] font-bold tracking-tight "
                        "text-[color:var(--purch-parchment)] "
                        "text-4xl sm:text-5xl lg:text-6xl leading-[1.02] mb-5"
                    ),
                ),
                rx.el.p(
                    "Log expenses the way you text — casually. Purch extracts the "
                    "item, amount, and category, and reacts in the tone you pick.",
                    class_name=(
                        "text-[color:var(--purch-muted)] text-base leading-relaxed "
                        "max-w-lg mb-6"
                    ),
                ),
                rx.el.div(
                    rx.foreach(_TONE_CHIPS, _tone_chip),
                    class_name="flex flex-wrap gap-2",
                ),
                rx.el.p(
                    f"{len(_TONE_CHIPS)} personality tones — including Rich Tita and Kapampangan",
                    class_name="text-xs text-[color:var(--purch-muted)] mt-4",
                ),
                class_name="mt-10",
            ),
            class_name="w-full max-w-xl px-6 sm:px-10 lg:px-16 py-14 lg:py-20",
        ),
        class_name=(
            "bg-[color:var(--purch-dark)] flex items-center justify-center "
            "min-h-[50vh] lg:min-h-[calc(100vh-3rem)]"
        ),
    )


def _preview_card() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.span(
                "PURCH RECEIPT",
                class_name="font-['DM_Mono'] text-[0.7rem] text-[color:var(--purch-gold)]",
            ),
            rx.el.span(
                "✨ Bestie",
                class_name="font-['DM_Mono'] text-[0.7rem] text-[color:var(--purch-muted)]",
            ),
            class_name=(
                "flex items-center justify-between "
                "bg-[color:var(--purch-dark)] px-4 py-2 rounded-t-2xl"
            ),
        ),
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    "bought a phone case for 350",
                    class_name="purch-bubble-user text-sm max-w-[80%]",
                ),
                class_name="flex justify-end mb-3",
            ),
            rx.el.div(
                rx.el.div(
                    "Logged! Phone case ₱350 under Shopping. 🛍️",
                    class_name="purch-bubble-assistant text-sm max-w-[80%]",
                ),
                class_name="flex justify-start mb-3",
            ),
            rx.el.div(
                rx.el.div(
                    "how much this week?",
                    class_name="purch-bubble-user text-sm max-w-[80%]",
                ),
                class_name="flex justify-end mb-3",
            ),
            rx.el.div(
                rx.el.div(
                    "You spent ₱2,450 this week — most of it on Food. 🍽️",
                    class_name="purch-bubble-assistant text-sm max-w-[80%]",
                ),
                class_name="flex justify-start",
            ),
            class_name="bg-[color:var(--purch-paper)] p-5 rounded-b-2xl",
        ),
        class_name=(
            "w-full max-w-md border border-[color:var(--purch-border)] "
            "rounded-2xl overflow-hidden shadow-[var(--purch-shadow-md)]"
        ),
    )


def _google_button() -> rx.Component:
    """Google sign-in trigger. Kept as a real event handler so phase 3
    can drop in the OAuth redirect without changing the UI wiring."""
    return rx.el.button(
        rx.el.span(
            "G",
            class_name=(
                "inline-flex items-center justify-center w-5 h-5 rounded-full "
                "bg-white text-[color:var(--purch-ink)] text-xs font-bold mr-1"
            ),
        ),
        rx.el.span("Continue with Google"),
        on_click=AuthState.begin_google_login,
        class_name=f"{CLASSES['primary_button']} w-full mt-4",
        type="button",
    )


def _oauth_status_banner() -> rx.Component:
    """Renders whatever state the OAuth flow is in. Currently the only
    non-idle state is `unavailable` (phase 2 placeholder), but the shape
    is set up so phase 3 can add `redirecting` and `error` branches
    without restructuring."""
    return rx.cond(
        AuthState.oauth_status == "unavailable",
        rx.el.div(
            rx.el.p(
                AuthState.oauth_error,
                class_name="text-sm text-[color:var(--purch-ink)] leading-relaxed m-0",
            ),
            rx.el.div(
                rx.el.a(
                    "Preview the chat →",
                    href=ROUTES["chat"],
                    class_name=(
                        "text-sm font-semibold text-[color:var(--purch-coral)] "
                        "hover:text-[color:var(--purch-coral-light)] transition-colors"
                    ),
                ),
                rx.el.button(
                    "Dismiss",
                    on_click=AuthState.clear_oauth_error,
                    class_name=(
                        "text-xs text-[color:var(--purch-muted)] "
                        "hover:text-[color:var(--purch-ink)] transition-colors"
                    ),
                ),
                class_name="flex items-center justify-between mt-3",
            ),
            class_name=(
                "mt-4 p-4 rounded-xl border border-[color:var(--purch-gold)] "
                "bg-[color:var(--purch-paper)]"
            ),
        ),
        rx.fragment(),
    )


def _sign_in_card() -> rx.Component:
    return rx.el.div(
        brand(show_beta=False, size="lg"),
        rx.el.h2(
            "Own it. Log it.",
            class_name=f"{CLASSES['display_heading']} text-2xl mt-4",
        ),
        rx.el.p(
            "Sign in with Google to start tracking the way you actually talk.",
            class_name="text-sm text-[color:var(--purch-secondary-text)] mt-1",
        ),
        _google_button(),
        _oauth_status_banner(),
        rx.el.div(
            rx.el.span(
                "Production note",
                class_name=(
                    "font-['DM_Mono'] text-[0.6rem] uppercase tracking-[0.12em] "
                    "text-[color:var(--purch-gold)]"
                ),
            ),
            rx.el.p(
                "OAuth credentials are configured server-side via environment "
                "variables — no secrets are shipped to the browser. See "
                "MIGRATION.md §7 for the shortlist of providers we're evaluating.",
                class_name="text-xs text-[color:var(--purch-muted)] leading-relaxed mt-1",
            ),
            class_name=(
                "mt-6 pt-4 border-t border-[color:var(--purch-border)]"
            ),
        ),
        rx.el.a(
            "← Back to home",
            href=ROUTES["index"],
            class_name=(
                "text-sm text-[color:var(--purch-muted)] "
                "hover:text-[color:var(--purch-coral)] mt-4 inline-block transition-colors"
            ),
        ),
        class_name=f"{CLASSES['card']} p-8 w-full max-w-md",
    )


def _sign_in_panel() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            _preview_card(),
            _sign_in_card(),
            class_name="flex flex-col items-center gap-6 w-full max-w-md",
        ),
        class_name=(
            "bg-[color:var(--purch-parchment)] flex items-center justify-center "
            "px-6 sm:px-10 lg:px-16 py-14 lg:py-20 "
            "min-h-[50vh] lg:min-h-[calc(100vh-3rem)]"
        ),
    )


def login_page() -> rx.Component:
    return page_shell(
        rx.el.div(
            _hero_panel(),
            _sign_in_panel(),
            class_name="grid grid-cols-1 lg:grid-cols-2 w-full",
        ),
        wide=True,
    )
