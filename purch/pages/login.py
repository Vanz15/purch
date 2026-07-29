"""Sign-in page — three real auth paths.

* **Google via Supabase** — click → server builds an authorize URL from
  the server-side `SUPABASE_URL` / `SUPABASE_KEY` and `rx.redirect`s to
  it. Callback lands back here with a `?code=` and completes.
* **Email + password** — one form, toggle between sign-in and sign-up.
* **Guest** — mints a fresh browser-local UUID identity. No shared
  anonymous access anywhere else in the app.

Design tokens (parchment background, espresso dark surfaces, coral
primary, gold highlights, Playfair display headings, soft bordered
paper cards) come from `assets/purch_theme.css` and `purch/theme.py`.
"""

from __future__ import annotations

import reflex as rx

from purch.components.brand import brand
from purch.components.layout import page_shell
from purch.states.auth_state import AuthState
from purch.theme import CLASSES, ROUTES


# ---------------------------------------------------------------------- #
# Small primitives
# ---------------------------------------------------------------------- #


def _hero_panel() -> rx.Component:
    """Left panel mirrors the public landing-page hero treatment."""
    tones = [
        "Nonchalant",
        "Bestie",
        "Sarcastic",
        "Coach",
        "Rich Tita",
        "Kapampangan",
    ]
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
                "Budget tracking, reimagined",
                class_name=CLASSES["eyebrow"],
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
                    f"{CLASSES['display_heading']} text-5xl sm:text-6xl "
                    "lg:text-7xl leading-[1.02] mt-3 "
                    "text-[color:var(--purch-parchment)]"
                ),
            ),
            rx.el.p(
                "Log expenses the way you text — casually. Purch extracts the "
                "item, amount, and category, and reacts in the tone you pick. "
                "No forms, no dropdowns — just chat.",
                class_name="mt-5 max-w-xl text-[color:var(--purch-muted)] leading-relaxed",
            ),
            rx.el.div(
                rx.foreach(
                    tones,
                    lambda tone: rx.el.span(tone, class_name="purch-chip"),
                ),
                class_name="flex flex-wrap gap-2 mt-6",
            ),
            rx.el.div(
                rx.el.a(
                    "Open the chat →",
                    href=ROUTES["chat"],
                    class_name=CLASSES["primary_button"],
                ),
                class_name="mt-8 flex flex-wrap items-center gap-3",
            ),
            class_name=(
                "flex flex-col justify-center gap-5 w-full px-6 sm:px-10 "
                "lg:px-16 py-16 lg:py-20"
            ),
        ),
        class_name="bg-[color:var(--purch-dark)] flex items-center",
    )


def _status_banner() -> rx.Component:
    """Success / info notice — coral-tinted paper card with a dismiss."""
    return rx.cond(
        AuthState.info_text != "",
        rx.el.div(
            rx.el.span(
                "✓", class_name="text-[color:var(--purch-teal)] font-bold"
            ),
            rx.el.p(
                AuthState.info_text,
                class_name="text-sm text-[color:var(--purch-ink)] flex-1 m-0",
            ),
            rx.el.button(
                "Dismiss",
                on_click=AuthState.dismiss_message,
                type="button",
                class_name=(
                    "text-xs text-[color:var(--purch-muted)] "
                    "hover:text-[color:var(--purch-ink)] transition-colors"
                ),
            ),
            class_name=(
                "flex items-center gap-3 mt-4 p-3 rounded-xl "
                "border border-[color:var(--purch-teal)] "
                "bg-[color:var(--purch-paper)]"
            ),
        ),
        rx.fragment(),
    )


def _error_banner() -> rx.Component:
    return rx.cond(
        AuthState.error_text != "",
        rx.el.div(
            rx.el.span(
                "⚠",
                class_name="text-[color:var(--purch-danger)] font-bold",
            ),
            rx.el.p(
                AuthState.error_text,
                class_name="text-sm text-[color:var(--purch-ink)] flex-1 m-0",
            ),
            rx.el.button(
                "Dismiss",
                on_click=AuthState.dismiss_message,
                type="button",
                class_name=(
                    "text-xs text-[color:var(--purch-muted)] "
                    "hover:text-[color:var(--purch-ink)] transition-colors"
                ),
            ),
            class_name=(
                "flex items-center gap-3 mt-4 p-3 rounded-xl "
                "border border-[color:var(--purch-danger)] "
                "bg-[color:var(--purch-paper)]"
            ),
        ),
        rx.fragment(),
    )


def _google_button() -> rx.Component:
    return rx.el.button(
        rx.el.span(
            "G",
            class_name=(
                "inline-flex items-center justify-center w-5 h-5 rounded-full "
                "bg-white text-[color:var(--purch-ink)] text-xs font-bold mr-2"
            ),
        ),
        rx.el.span(
            rx.cond(AuthState.is_busy, "Please wait…", "Continue with Google"),
        ),
        on_click=AuthState.begin_google_login,
        disabled=AuthState.is_busy,
        type="button",
        class_name=(
            f"{CLASSES['primary_button']} w-full "
            "disabled:opacity-60 disabled:cursor-not-allowed"
        ),
    )


def _divider(label: str) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            class_name="flex-1 h-px bg-[color:var(--purch-border)]",
        ),
        rx.el.span(
            label,
            class_name=(
                "font-['DM_Mono'] text-[0.65rem] uppercase "
                "tracking-[0.1em] text-[color:var(--purch-muted)] px-3"
            ),
        ),
        rx.el.div(
            class_name="flex-1 h-px bg-[color:var(--purch-border)]",
        ),
        class_name="flex items-center my-5",
    )


def _labelled_input(
    label: str,
    name: str,
    input_type: str,
    placeholder: str,
    auto_complete: str,
) -> rx.Component:
    """Uncontrolled input — the form submit reads values from form_data
    so we don't have to remount the input on every keystroke."""
    return rx.el.label(
        rx.el.span(
            label,
            class_name=(
                "font-['DM_Mono'] text-[0.65rem] uppercase "
                "tracking-[0.1em] text-[color:var(--purch-muted)]"
            ),
        ),
        rx.el.input(
            name=name,
            type=input_type,
            placeholder=placeholder,
            auto_complete=auto_complete,
            disabled=AuthState.is_busy,
            class_name=(
                "mt-1 w-full rounded-xl border border-[color:var(--purch-border)] "
                "bg-[color:var(--purch-paper)] px-3.5 py-2.5 text-sm "
                "placeholder:text-[color:var(--purch-muted)] focus:outline-none "
                "focus:border-[color:var(--purch-coral)] "
                "disabled:opacity-60 disabled:cursor-not-allowed"
            ),
        ),
        class_name="flex flex-col gap-1",
    )


def _forgot_password_link() -> rx.Component:
    """Small inline link under the password field, sign-in mode only.
    Kept visually restrained (muted → coral on hover) so it doesn't
    compete with the primary Sign in CTA."""
    return rx.cond(
        ~AuthState.is_signup_mode,
        rx.el.div(
            rx.el.button(
                "Forgot password?",
                on_click=AuthState.open_recovery,
                type="button",
                disabled=AuthState.is_busy,
                class_name=(
                    "text-xs font-semibold text-[color:var(--purch-muted)] "
                    "hover:text-[color:var(--purch-coral)] transition-colors "
                    "disabled:opacity-60 disabled:cursor-not-allowed"
                ),
            ),
            class_name="flex justify-end -mt-1",
        ),
        rx.fragment(),
    )


def _email_form() -> rx.Component:
    return rx.el.form(
        rx.cond(
            AuthState.is_signup_mode,
            _labelled_input(
                "Display name (optional)",
                "name",
                "text",
                "How Purch should address you",
                "name",
            ),
            rx.fragment(),
        ),
        _labelled_input(
            "Email",
            "email",
            "email",
            "you@example.com",
            "email",
        ),
        _labelled_input(
            "Password",
            "password",
            "password",
            "At least 6 characters",
            "current-password",
        ),
        _forgot_password_link(),
        rx.el.button(
            AuthState.submit_label,
            type="submit",
            disabled=AuthState.is_busy,
            class_name=(
                f"{CLASSES['primary_button']} w-full mt-2 "
                "disabled:opacity-60 disabled:cursor-not-allowed"
            ),
        ),
        rx.el.button(
            AuthState.toggle_prompt,
            on_click=AuthState.toggle_mode,
            type="button",
            disabled=AuthState.is_busy,
            class_name=(
                "text-xs text-[color:var(--purch-muted)] "
                "hover:text-[color:var(--purch-coral)] transition-colors "
                "mt-2 self-center"
            ),
        ),
        on_submit=AuthState.submit_credentials,
        reset_on_submit=False,
        class_name="flex flex-col gap-3",
    )


def _recovery_form() -> rx.Component:
    """Forgot-password form. Preserves the espresso/coral card language:
    parchment card, DM Mono labels, coral primary button, muted back
    link. The response is intentionally neutral so we don't leak
    whether an address exists."""
    return rx.el.form(
        rx.el.div(
            rx.el.h3(
                "Reset your password",
                class_name=(
                    "font-['Playfair_Display'] font-bold text-lg "
                    "text-[color:var(--purch-ink)] m-0"
                ),
            ),
            rx.el.p(
                "Enter the email you signed up with and we'll send a "
                "recovery link. If you don't receive one shortly, check "
                "your spam folder or try again in a few minutes.",
                class_name=(
                    "text-xs text-[color:var(--purch-muted)] mt-1 "
                    "leading-relaxed m-0"
                ),
            ),
            class_name="mb-1",
        ),
        rx.el.label(
            rx.el.span(
                "Email",
                class_name=(
                    "font-['DM_Mono'] text-[0.65rem] uppercase "
                    "tracking-[0.1em] text-[color:var(--purch-muted)]"
                ),
            ),
            rx.el.input(
                name="recovery_email",
                type="email",
                placeholder="you@example.com",
                auto_complete="email",
                default_value=AuthState.recovery_email,
                disabled=AuthState.is_busy,
                class_name=(
                    "mt-1 w-full rounded-xl border border-[color:var(--purch-border)] "
                    "bg-[color:var(--purch-paper)] px-3.5 py-2.5 text-sm "
                    "placeholder:text-[color:var(--purch-muted)] focus:outline-none "
                    "focus:border-[color:var(--purch-coral)] "
                    "disabled:opacity-60 disabled:cursor-not-allowed"
                ),
            ),
            class_name="flex flex-col gap-1",
        ),
        rx.el.button(
            rx.cond(
                AuthState.is_busy,
                "Sending\u2026",
                "Send recovery link",
            ),
            type="submit",
            disabled=AuthState.is_busy,
            class_name=(
                f"{CLASSES['primary_button']} w-full mt-2 "
                "disabled:opacity-60 disabled:cursor-not-allowed"
            ),
        ),
        rx.el.button(
            "\u2190 Back to sign in",
            on_click=AuthState.close_recovery,
            type="button",
            disabled=AuthState.is_busy,
            class_name=(
                "text-xs text-[color:var(--purch-muted)] "
                "hover:text-[color:var(--purch-coral)] transition-colors "
                "mt-1 self-center"
            ),
        ),
        on_submit=AuthState.submit_recovery,
        reset_on_submit=False,
        class_name=(
            "flex flex-col gap-3 p-4 rounded-xl "
            "border border-[color:var(--purch-border)] "
            "bg-[color:var(--purch-parchment)]"
        ),
    )


def _guest_card() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.h3(
                "Prefer not to sign up?",
                class_name=(
                    "font-['Playfair_Display'] font-bold text-base "
                    "text-[color:var(--purch-ink)]"
                ),
            ),
            rx.el.p(
                "Start a private guest session — your chat, budgets, and "
                "history stay on this device only. No email required.",
                class_name=(
                    "text-xs text-[color:var(--purch-muted)] leading-relaxed mt-1"
                ),
            ),
            class_name="w-full min-w-0",
        ),
        rx.el.button(
            rx.cond(
                AuthState.is_busy,
                "Please wait…",
                "Continue as guest",
            ),
            on_click=AuthState.sign_in_as_guest,
            disabled=AuthState.is_busy,
            type="button",
            class_name=(
                CLASSES["outline_button"]
                + " text-sm shrink-0 w-full sm:w-auto "
                + "disabled:opacity-60 disabled:cursor-not-allowed"
            ),
        ),
        class_name=(
            "flex flex-col items-stretch sm:flex-row sm:items-center gap-4 mt-5 "
            "p-4 rounded-xl border border-dashed border-[color:var(--purch-border)] "
            "bg-[color:var(--purch-parchment)]"
        ),
    )


def _session_status() -> rx.Component:
    """Rendered when the browser already has an active identity. Gives
    the user a clear path to continue OR to sign out (guest sessions
    are private to this browser, so it's important they can end them)."""
    return rx.el.div(
        rx.el.div(
            rx.el.span(
                "Currently signed in",
                class_name=(
                    "font-['DM_Mono'] text-[0.65rem] uppercase "
                    "tracking-[0.1em] text-[color:var(--purch-muted)]"
                ),
            ),
            rx.el.p(
                AuthState.display_name,
                class_name=(
                    "font-['Playfair_Display'] font-bold text-lg "
                    "text-[color:var(--purch-ink)] mt-1 m-0"
                ),
            ),
            rx.el.p(
                rx.match(
                    AuthState.auth_method,
                    ("google", "Signed in with Google"),
                    ("email", AuthState.user_email),
                    ("guest", "Guest session on this device"),
                    "Session active",
                ),
                class_name="text-xs text-[color:var(--purch-muted)] mt-0.5 m-0",
            ),
            class_name="flex-1 min-w-0",
        ),
        rx.el.div(
            rx.el.a(
                "Open chat →",
                href=ROUTES["chat"],
                class_name=CLASSES["primary_button"] + " text-sm",
            ),
            rx.el.button(
                "Sign out",
                on_click=AuthState.sign_out,
                type="button",
                class_name=CLASSES["outline_button"] + " text-sm",
            ),
            class_name="flex flex-col sm:flex-row gap-2 shrink-0",
        ),
        class_name=(
            "flex flex-col sm:flex-row sm:items-center gap-4 "
            "p-5 rounded-2xl border border-[color:var(--purch-teal)]/50 "
            "bg-[color:var(--purch-paper)]"
        ),
    )


def _sign_in_card() -> rx.Component:
    return rx.el.div(
        brand(show_beta=False, size="lg"),
        rx.el.h2(
            "Own it. Log it.",
            class_name=f"{CLASSES['display_heading']} text-2xl mt-4",
        ),
        rx.el.p(
            "Choose how you'd like to sign in. All three keep your data "
            "tied to a single identity — nothing is shared across users.",
            class_name=(
                "text-sm text-[color:var(--purch-secondary-text)] mt-1"
            ),
        ),
        rx.cond(
            AuthState.is_authenticated,
            rx.el.div(_session_status(), class_name="mt-5"),
            rx.fragment(),
        ),
        rx.el.div(
            _google_button(),
            _divider(
                rx.cond(
                    AuthState.is_recover_mode,
                    "or reset your password",
                    "or with email",
                ).to(str),
            ),
            rx.cond(
                AuthState.is_recover_mode,
                _recovery_form(),
                _email_form(),
            ),
            rx.cond(
                AuthState.is_recover_mode,
                rx.fragment(),
                _guest_card(),
            ),
            _error_banner(),
            _status_banner(),
            class_name="mt-6",
        ),
        rx.el.a(
            "← Back to home",
            href=ROUTES["index"],
            class_name=(
                "text-sm text-[color:var(--purch-muted)] "
                "hover:text-[color:var(--purch-coral)] mt-6 inline-block "
                "transition-colors"
            ),
        ),
        class_name=f"{CLASSES['card']} p-8 w-full max-w-md",
    )


def _sign_in_panel() -> rx.Component:
    return rx.el.section(
        _sign_in_card(),
        class_name=(
            "bg-[color:var(--purch-parchment)] flex items-center justify-center "
            "px-6 sm:px-10 lg:px-16 py-14 lg:py-20 "
            "min-h-[50vh] lg:min-h-screen"
        ),
    )


def login_page() -> rx.Component:
    return page_shell(
        rx.el.div(
            _hero_panel(),
            _sign_in_panel(),
            class_name="grid grid-cols-1 lg:grid-cols-2 w-full min-h-screen",
            on_mount=AuthState.handle_oauth_callback,
        ),
        wide=True,
        show_header=False,
    )
