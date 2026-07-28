"""Chat page — stateful conversation shell.

Phase 2 wires up the full UX loop (composer, message list with
timestamps, prompt chips, error banner, pending indicator, clear-chat
confirmation) against a local deterministic stub in `ChatState`. Phase 3
swaps the stub for `agent.graph.run_agent` — no changes required in this
file.
"""

import reflex as rx

from app.app.components.chat_bubble import chat_bubble, typing_indicator
from app.app.components.layout import page_shell
from app.app.states.chat_state import PROMPT_CHIPS, ChatState
from app.app.theme import CLASSES


def _prompt_chip(prompt: str) -> rx.Component:
    return rx.el.button(
        prompt,
        on_click=lambda: ChatState.use_prompt(prompt),
        type="button",
        class_name=(
            "px-3 py-1.5 rounded-full text-xs font-semibold "
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
            "Just type what you bought and I'll handle the rest. No forms, no "
            "dropdowns — just chat.",
            class_name=(
                "text-sm text-[color:var(--purch-muted)] mt-2 max-w-sm "
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
                    "bg-[color:var(--purch-paper)] px-4 py-3 text-sm "
                    "placeholder:text-[color:var(--purch-muted)] focus:outline-none "
                    "focus:border-[color:var(--purch-coral)] "
                    "disabled:opacity-60 disabled:cursor-not-allowed"
                ),
            ),
            rx.el.button(
                rx.cond(ChatState.is_sending, "Sending…", "Send"),
                type="submit",
                disabled=ChatState.is_sending,
                class_name=(
                    f"{CLASSES['primary_button']} min-w-[6rem] "
                    "disabled:opacity-60 disabled:cursor-not-allowed"
                ),
            ),
            class_name="flex items-center gap-2",
        ),
        on_submit=ChatState.send_message,
        reset_on_submit=True,
        class_name="mt-4",
    )


def _header_row() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div("Chat", class_name=CLASSES["eyebrow"]),
            rx.el.h2(
                "Talk to Purch",
                class_name=f"{CLASSES['display_heading']} text-xl mt-0.5",
            ),
            class_name="flex-1 min-w-0",
        ),
        _clear_controls(),
        class_name="flex items-start justify-between gap-3 mb-4",
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


def _preview_note() -> rx.Component:
    return rx.el.div(
        rx.el.span("Phase 2 preview", class_name=CLASSES["eyebrow"]),
        rx.el.p(
            "Replies are generated locally so the UI can be reviewed end-to-end. "
            "The real LangGraph agent + database wire in next.",
            class_name="text-xs text-[color:var(--purch-muted)] leading-relaxed mt-1 m-0",
        ),
        class_name=(
            "mt-3 px-3 py-2 rounded-lg bg-[color:var(--purch-paper)] "
            "border border-dashed border-[color:var(--purch-border)]"
        ),
    )


def chat_page() -> rx.Component:
    return page_shell(
        rx.el.div(
            rx.el.div(
                _header_row(),
                _error_banner(),
                rx.cond(
                    ChatState.has_messages, _message_list(), _empty_state()
                ),
                _composer(),
                _preview_note(),
                class_name=f"{CLASSES['card']} p-6 sm:p-8",
            ),
            class_name="max-w-3xl mx-auto w-full",
        ),
    )
