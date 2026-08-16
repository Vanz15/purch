"""Chat page — stateful conversation shell (phase 2 UI, local stub replies)."""

import reflex as rx

from purch.components.chat_bubble import chat_bubble, typing_indicator
from purch.components.layout import page_shell
from purch.states.auth_state import AuthState
from purch.states.chat_state import PROMPT_CHIPS, ChatState, WalletChoice
from purch.theme import CLASSES, ROUTES


def _prompt_chip(prompt: str) -> rx.Component:
    return rx.el.button(
        prompt,
        on_click=lambda: ChatState.use_prompt(prompt),
        type="button",
        class_name=(
            "px-3.5 py-2 rounded-full text-sm font-semibold "
            "bg-[color:var(--purch-paper)] border border-[color:var(--purch-border)] "
            "text-[color:var(--purch-ink)] hover:border-[color:var(--purch-coral)] "
            "hover:text-[color:var(--purch-coral)] transition-colors"
        ),
    )


def _empty_state() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            "P",
            class_name=(
                "w-16 h-16 rounded-2xl bg-[color:var(--purch-dark)] "
                "text-[color:var(--purch-gold)] font-['Playfair_Display'] font-bold "
                "text-3xl flex items-center justify-center purch-rise"
            ),
        ),
        rx.el.h3(
            "Hey! I'm Purch.",
            class_name=f"{CLASSES['display_heading']} text-xl mt-4",
        ),
        rx.el.p(
            "Tell me what you bought, ask what you spent, or set a budget. "
            "No forms, no dropdowns — just a quick, natural chat.",
            class_name=(
                "text-base text-[color:var(--purch-muted)] mt-3 max-w-md "
                "text-center leading-relaxed"
            ),
        ),
        rx.el.div(
            rx.foreach(PROMPT_CHIPS, _prompt_chip),
            class_name="flex flex-wrap justify-center gap-2 mt-6 max-w-md",
        ),
        class_name="flex flex-col items-center justify-center py-12 sm:py-16",
    )


def _message_list() -> rx.Component:
    return rx.el.div(
        rx.foreach(ChatState.messages, chat_bubble),
        rx.cond(ChatState.is_sending, typing_indicator(), rx.fragment()),
        class_name="flex flex-col py-4 min-h-[300px]",
    )


def _error_banner() -> rx.Component:
    return rx.cond(
        ChatState.error_text != "",
        rx.el.div(
            rx.el.span(
                "⚠", class_name="text-[color:var(--purch-danger)] font-bold"
            ),
            rx.el.p(
                ChatState.error_text,
                class_name="text-sm text-[color:var(--purch-ink)] flex-1 m-0",
            ),
            rx.el.button(
                "Dismiss",
                on_click=ChatState.dismiss_error,
                type="button",
                class_name=(
                    "text-xs text-[color:var(--purch-muted)] "
                    "hover:text-[color:var(--purch-ink)] transition-colors"
                ),
            ),
            class_name=(
                "flex items-center gap-3 mb-3 p-3 rounded-xl "
                "border border-[color:var(--purch-danger)] "
                "bg-[color:var(--purch-paper)]"
            ),
        ),
        rx.fragment(),
    )


def _composer() -> rx.Component:
    return rx.el.form(
        rx.el.div(
            rx.el.input(
                name="draft",
                placeholder='Try "milk tea ₱85" or "how much this week?"',
                default_value=ChatState.draft,
                key=ChatState.draft_version,
                disabled=ChatState.is_sending,
                auto_complete="off",
                class_name=(
                    "flex-1 rounded-xl border border-[color:var(--purch-border)] "
                    "bg-[color:var(--purch-paper)] px-4 py-3.5 text-base "
                    "placeholder:text-[color:var(--purch-muted)] focus:outline-none "
                    "focus:border-[color:var(--purch-coral)] "
                    "disabled:opacity-60 disabled:cursor-not-allowed "
                    "w-full min-w-0 sm:flex-1"
                ),
            ),
            rx.el.button(
                rx.cond(ChatState.is_sending, "Sending…", "Send"),
                type="submit",
                disabled=ChatState.is_sending,
                class_name=(
                    f"{CLASSES['primary_button']} min-w-[6.5rem] text-base "
                    "disabled:opacity-60 disabled:cursor-not-allowed "
                    "w-full sm:w-auto sm:shrink-0"
                ),
            ),
            class_name="flex flex-col sm:flex-row items-stretch sm:items-center gap-2",
        ),
        on_submit=ChatState.send_message,
        reset_on_submit=True,
        class_name="mt-4",
    )


def _wallet_chip(choice: WalletChoice) -> rx.Component:
    return rx.el.button(
        rx.el.span(
            choice["name"],
            class_name="text-sm font-semibold",
        ),
        rx.el.span(
            rx.el.span("₱", choice["balance_display"]),
            class_name=(
                "font-['DM_Mono'] text-[0.65rem] "
                "text-[color:var(--purch-muted)]"
            ),
        ),
        on_click=lambda: ChatState.choose_wallet(choice["id"]),
        type="button",
        class_name=(
            "flex flex-col items-start gap-0.5 px-3.5 py-2 rounded-xl "
            "bg-[color:var(--purch-paper)] border "
            "border-[color:var(--purch-border)] "
            "text-[color:var(--purch-ink)] "
            "hover:border-[color:var(--purch-teal)] "
            "hover:text-[color:var(--purch-teal)] transition-colors"
        ),
    )


def _wallet_choice_row() -> rx.Component:
    """Clickable wallet chips shown when a logged purchase still needs a
    wallet. Buttons (not typing) so nicknames can never be misspelled."""
    return rx.cond(
        ChatState.has_wallet_choices,
        rx.el.div(
            rx.el.div(
                "Pick a wallet",
                class_name=CLASSES["eyebrow"],
            ),
            rx.el.div(
                rx.foreach(ChatState.wallet_choices, _wallet_chip),
                class_name="flex flex-wrap gap-2 mt-2",
            ),
            rx.el.button(
                "Skip for now",
                on_click=ChatState.skip_wallet,
                type="button",
                class_name=(
                    "text-xs text-[color:var(--purch-muted)] "
                    "hover:text-[color:var(--purch-coral)] "
                    "transition-colors mt-3"
                ),
            ),
            class_name=(
                "mt-2 p-4 rounded-xl border border-dashed "
                "border-[color:var(--purch-border)] "
                "bg-[color:var(--purch-parchment)]"
            ),
        ),
        rx.fragment(),
    )


def _clear_controls() -> rx.Component:
    return rx.cond(
        ChatState.has_messages,
        rx.cond(
            ChatState.confirm_clear,
            rx.el.div(
                rx.el.span(
                    "Clear conversation?",
                    class_name="text-xs text-[color:var(--purch-muted)] mr-1",
                ),
                rx.el.button(
                    "Cancel",
                    on_click=ChatState.cancel_clear,
                    type="button",
                    class_name=CLASSES["outline_button"]
                    + " text-xs py-1.5 px-3",
                ),
                rx.el.button(
                    "Confirm",
                    on_click=ChatState.confirm_clear_chat,
                    type="button",
                    class_name=CLASSES["primary_button"]
                    + " text-xs py-1.5 px-3",
                ),
                class_name="flex items-center gap-2",
            ),
            rx.el.button(
                "↺ Clear chat",
                on_click=ChatState.request_clear,
                type="button",
                class_name=(
                    "text-xs text-[color:var(--purch-muted)] "
                    "hover:text-[color:var(--purch-coral)] transition-colors"
                ),
            ),
        ),
        rx.fragment(),
    )


def _header_row() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div("Chat", class_name=CLASSES["eyebrow"]),
            rx.el.h2(
                "Talk to Purch",
                class_name=f"{CLASSES['display_heading']} text-2xl sm:text-3xl mt-1",
            ),
            class_name="flex-1 min-w-0",
        ),
        _clear_controls(),
        class_name="flex items-start justify-between gap-3 mb-4",
    )


def _unauthenticated_prompt() -> rx.Component:
    """Rendered when no AuthState identity is active. Preserves the
    espresso/parchment card look and offers both the sign-in and
    continue-as-guest paths, matching the login screen's CTAs."""
    return rx.el.div(
        rx.el.div(
            "P",
            class_name=(
                "w-16 h-16 rounded-2xl bg-[color:var(--purch-dark)] "
                "text-[color:var(--purch-gold)] font-['Playfair_Display'] font-bold "
                "text-3xl flex items-center justify-center"
            ),
        ),
        rx.el.h3(
            "Sign in to start chatting.",
            class_name=f"{CLASSES['display_heading']} text-2xl mt-4",
        ),
        rx.el.p(
            "Purch keeps every purchase, budget, and tone tied to your account. "
            "Sign in with Google or email — or continue as a guest to preview "
            "the experience privately on this device.",
            class_name=(
                "text-base text-[color:var(--purch-muted)] mt-3 max-w-md "
                "text-center leading-relaxed"
            ),
        ),
        rx.el.div(
            rx.el.a(
                "Sign in",
                href=ROUTES["login"],
                class_name=CLASSES["primary_button"],
            ),
            rx.el.button(
                "Continue as guest",
                on_click=AuthState.sign_in_as_guest,
                type="button",
                class_name=CLASSES["outline_button"],
            ),
            class_name="flex flex-wrap items-center justify-center gap-3 mt-6",
        ),
        class_name="flex flex-col items-center justify-center py-12 sm:py-16",
    )


def _authenticated_body() -> rx.Component:
    return rx.el.div(
        _header_row(),
        _error_banner(),
        rx.cond(ChatState.has_messages, _message_list(), _empty_state()),
        _wallet_choice_row(),
        _composer(),
    )


def chat_page() -> rx.Component:
    return page_shell(
        rx.el.div(
            rx.el.div(
                rx.cond(
                    AuthState.is_authenticated,
                    _authenticated_body(),
                    _unauthenticated_prompt(),
                ),
                class_name=f"{CLASSES['card']} p-3 sm:p-6 lg:p-8",
            ),
            class_name="max-w-3xl mx-auto w-full",
            on_mount=[
                ChatState.on_load,
                rx.call_script(
                    "Intl.DateTimeFormat().resolvedOptions().timeZone",
                    callback=ChatState.set_timezone,
                ),
            ],
        ),
        with_sidebar=True,
    )
