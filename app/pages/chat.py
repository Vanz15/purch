"""Chat page shell. The actual conversation loop (agent invocation,
message history, tone-aware replies) is wired in a later phase — this
file just stands up the visual container and empty state."""

import reflex as rx

from app.components.layout import page_shell
from app.theme import CLASSES


def _empty_state() -> rx.Component:
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
            "Hey! I'm Purch.",
            class_name=f"{CLASSES['display_heading']} text-xl mt-4",
        ),
        rx.el.p(
            "Just type what you bought and I'll handle the rest. No forms, no dropdowns — just chat.",
            class_name="text-sm text-[color:var(--purch-muted)] mt-2 max-w-sm text-center leading-relaxed",
        ),
        class_name="flex flex-col items-center justify-center py-16",
    )


def _composer() -> rx.Component:
    return rx.el.div(
        rx.el.input(
            placeholder='Try "milk tea ₱85" or "how much this week?"',
            disabled=True,
            class_name=(
                "flex-1 rounded-xl border border-[color:var(--purch-border)] "
                "bg-[color:var(--purch-paper)] px-4 py-3 text-sm "
                "placeholder:text-[color:var(--purch-muted)] focus:outline-none "
                "focus:border-[color:var(--purch-coral)]"
            ),
        ),
        rx.el.button(
            "Send",
            disabled=True,
            class_name=f"{CLASSES['primary_button']} opacity-70 cursor-not-allowed",
        ),
        class_name="flex items-center gap-2 mt-6",
    )


def chat_page() -> rx.Component:
    return page_shell(
        rx.el.div(
            rx.el.div(
                _empty_state(),
                _composer(),
                class_name=f"{CLASSES['card']} p-6 sm:p-10",
            ),
            class_name="max-w-3xl mx-auto",
        ),
    )
