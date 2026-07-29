"""Chat bubble component.

Assistant bubbles pick up a coloured border when the message carries a
budget alert (warning = gold, danger = red).
"""

import reflex as rx

from purch.states.chat_state import ChatMessage


def _assistant_avatar() -> rx.Component:
    return rx.el.div(
        "P",
        class_name=(
            "w-8 h-8 rounded-full bg-[color:var(--purch-dark)] "
            "text-[color:var(--purch-gold)] font-['Playfair_Display'] font-bold "
            "text-sm flex items-center justify-center flex-shrink-0 mt-0.5"
        ),
    )


def _alert_header(alert: rx.Var) -> rx.Component:
    return rx.match(
        alert,
        (
            "warning",
            rx.el.div(
                rx.el.span("⚠"),
                rx.el.span("Budget warning"),
                class_name=(
                    "flex items-center gap-1.5 font-['Playfair_Display'] font-bold "
                    "text-[0.65rem] uppercase tracking-[0.1em] mb-2 "
                    "text-[color:var(--purch-gold)]"
                ),
            ),
        ),
        (
            "danger",
            rx.el.div(
                rx.el.span("⚠"),
                rx.el.span("Over budget"),
                class_name=(
                    "flex items-center gap-1.5 font-['Playfair_Display'] font-bold "
                    "text-[0.65rem] uppercase tracking-[0.1em] mb-2 "
                    "text-[color:var(--purch-danger)]"
                ),
            ),
        ),
        rx.fragment(),
    )


def _assistant_bubble(msg: ChatMessage) -> rx.Component:
    return rx.el.div(
        _assistant_avatar(),
        rx.el.div(
            rx.el.div(
                _alert_header(msg["alert"]),
                rx.el.p(
                    msg["text"],
                    class_name="text-base leading-7 whitespace-pre-wrap m-0",
                ),
                rx.cond(
                    msg["meta"] != "",
                    rx.el.div(
                        msg["meta"],
                        class_name=(
                            "mt-2 pt-2 border-t border-dashed border-[color:var(--purch-border)] "
                            "font-['DM_Mono'] text-xs text-[color:var(--purch-muted)]"
                        ),
                    ),
                    rx.fragment(),
                ),
                class_name=rx.match(
                    msg["alert"],
                    (
                        "warning",
                        "purch-bubble-assistant border-2 border-[color:var(--purch-gold)]",
                    ),
                    (
                        "danger",
                        "purch-bubble-assistant border-2 border-[color:var(--purch-danger)]",
                    ),
                    "purch-bubble-assistant",
                ),
            ),
            rx.el.div(
                msg["time"],
                class_name="text-xs text-[color:var(--purch-muted)] mt-1.5 ml-1",
            ),
            class_name="max-w-[92%] sm:max-w-[85%] lg:max-w-[80%] min-w-0",
        ),
        class_name="flex justify-start items-start gap-2 mb-4",
    )


def _user_bubble(msg: ChatMessage) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.p(
                msg["text"],
                class_name="text-[0.9rem] leading-relaxed whitespace-pre-wrap m-0",
            ),
            class_name="purch-bubble-user",
        ),
        rx.el.div(
            msg["time"],
            class_name="text-xs text-[color:var(--purch-muted)] mt-1.5 mr-1 text-right",
        ),
        class_name=(
            "max-w-[92%] sm:max-w-[85%] lg:max-w-[80%] min-w-0 "
            "flex flex-col items-end ml-auto self-end"
        ),
    )


def chat_bubble(msg: ChatMessage) -> rx.Component:
    return rx.cond(
        msg["role"] == "user", _user_bubble(msg), _assistant_bubble(msg)
    )


def typing_indicator() -> rx.Component:
    dot_class = (
        "w-1.5 h-1.5 rounded-full bg-[color:var(--purch-muted)] animate-pulse"
    )
    return rx.el.div(
        rx.el.div(
            "P",
            class_name=(
                "w-8 h-8 rounded-full bg-[color:var(--purch-dark)] "
                "text-[color:var(--purch-gold)] font-['Playfair_Display'] font-bold "
                "text-sm flex items-center justify-center flex-shrink-0"
            ),
        ),
        rx.el.div(
            rx.el.div(class_name=dot_class),
            rx.el.div(class_name=f"{dot_class} [animation-delay:150ms]"),
            rx.el.div(class_name=f"{dot_class} [animation-delay:300ms]"),
            class_name="purch-bubble-assistant flex items-center gap-1.5 py-3",
        ),
        class_name="flex justify-start items-center gap-2 mb-4",
    )
